"""
拍照购完整流程脚本 —— 独立执行入口，供调试、优化和批量测试使用。

使用方式：
  # 通过 task_id 执行（从数据库取任务）
  python -m app.workers.pdd_photo.run_flow --task-id 123

  # 直接指定图片和设备执行（无需数据库）
  python -m app.workers.pdd_photo.run_flow \
    --device emulator-5554 \
    --image-url "https://example.com/product.jpg" \
    --max-candidates 4

  # 使用本地图片文件
  python -m app.workers.pdd_photo.run_flow \
    --device emulator-5554 \
    --local-image /tmp/test.jpg

输出：
  - 实时打印每个步骤的耗时
  - 生成完整的 JSON 结果报告
  - 可选保存截图和 XML dump
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional

import httpx

# 确保项目根目录在 sys.path 中
project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from app.config import get_settings
from app.database import SessionLocal
from app.models.product import Product
from app.services import photo_search_service
from app.workers.pdd_photo.adb_client import AdbClient
from app.workers.pdd_photo.link_extractor import fill_product_links_from_detail_taps
from app.workers.pdd_photo.artifact_manager import ArtifactManager
from app.workers.pdd_photo.device_manager import DeviceManager
from app.workers.pdd_photo.device_lock import DeviceLock
from app.workers.pdd_photo.pdd_photo_flow import FlowContext, FlowError, PddPhotoFlow
from app.workers.pdd_photo.result_parser import ResultParser

logger = logging.getLogger("pdd_photo_flow")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

DOWNLOAD_TIMEOUT = 30


class FlowRunner:
    """拍照购流程执行器，封装完整的执行链路。"""

    def __init__(
        self,
        device_serial: str,
        task_id: int = 0,
        source_image_url: Optional[str] = None,
        local_image_path: Optional[str] = None,
        max_candidates: int = 4,
        fetch_pdd_links: bool = True,
        user_id: Optional[int] = None,
    ):
        self.device_serial = device_serial
        self.task_id = task_id
        self.source_image_url = source_image_url
        self.local_image_path = local_image_path
        self.max_candidates = max_candidates
        self.fetch_pdd_links = fetch_pdd_links
        self.user_id = user_id

        self.artifacts = ArtifactManager(task_id)
        self.step_logs: list = []
        self.local_image: Optional[str] = None
        self.ctx: Optional[FlowContext] = None

    def run(self) -> dict:
        """执行完整流程，返回结果字典。"""
        overall_start = time.monotonic()
        result = {
            "task_id": self.task_id,
            "device_serial": self.device_serial,
            "status": "running",
            "steps": [],
            "candidates": [],
            "saved_count": 0,
            "total_elapsed_ms": 0,
            "error": None,
        }

        try:
            # ── 1. 设备预热 ────────────────────────────────────
            t0 = time.monotonic()
            mgr = DeviceManager(SessionLocal())
            if not mgr.warm_up(self.device_serial):
                raise RuntimeError("设备预热失败")
            elapsed = int((time.monotonic() - t0) * 1000)
            self._log("PRECHECK", "设备预热完成", True, elapsed)
            result["steps"].append({"step": "PRECHECK", "action": "设备预热完成", "elapsed_ms": elapsed})

            # ── 2. 下载/准备图片 ───────────────────────────────
            t0 = time.monotonic()
            if self.local_image_path:
                self.local_image = self.local_image_path
            elif self.source_image_url:
                self.local_image = self._download_image(self.source_image_url)
                if not self.local_image:
                    raise RuntimeError(f"图片下载失败: {self.source_image_url}")
            else:
                raise RuntimeError("未指定图片源（--image-url 或 --local-image）")
            elapsed = int((time.monotonic() - t0) * 1000)
            self._log("DOWNLOAD", f"图片准备完成: {self.local_image}", True, elapsed)
            result["steps"].append({"step": "DOWNLOAD", "action": f"图片: {Path(self.local_image).name}", "elapsed_ms": elapsed})

            # ── 3. 执行拍照购流程 ──────────────────────────────
            self.ctx = FlowContext(
                serial=self.device_serial,
                task_id=self.task_id,
                local_image_path=self.local_image,
                remote_image_filename=f"gp_pdd_{self.task_id or 'test'}.jpg",
            )
            flow = PddPhotoFlow(self.ctx)

            t0 = time.monotonic()
            step_logs = flow.execute()
            flow_elapsed = int((time.monotonic() - t0) * 1000)

            for sl in step_logs:
                self._log(sl.step, sl.action, sl.success, sl.elapsed_ms, sl.message)
                result["steps"].append({
                    "step": sl.step,
                    "action": sl.action,
                    "success": sl.success,
                    "elapsed_ms": sl.elapsed_ms,
                    "message": sl.message,
                })

            # ── 4. 解析结果 ────────────────────────────────────
            for p in self.ctx.result_xml_paths:
                self.artifacts.save_xml(p, "result")
            for p in self.ctx.result_screenshots:
                self.artifacts.save_screenshot(p, "result")

            t0 = time.monotonic()
            parser = ResultParser()
            parse_result = parser.parse_xml_files(self.ctx.result_xml_paths)
            parse_elapsed = int((time.monotonic() - t0) * 1000)
            self._log("PARSE", f"解析完成 {len(parse_result.candidates)} 个候选", True, parse_elapsed)
            result["steps"].append({"step": "PARSE", "action": f"解析 {len(parse_result.candidates)} 个候选", "elapsed_ms": parse_elapsed})

            cap = self.max_candidates
            candidates = parse_result.candidates[:cap]

            # ── 5. 提取商品链接 ────────────────────────────────
            if self.fetch_pdd_links and get_settings().PDD_EXTRACT_PRODUCT_LINKS and candidates:
                t0 = time.monotonic()
                adb_links = AdbClient(serial=self.device_serial)
                adb_links.kill_uiautomator()
                n_ok = fill_product_links_from_detail_taps(adb_links, candidates, max_items=cap)
                extract_elapsed = int((time.monotonic() - t0) * 1000)
                self._log("EXTRACT_LINKS", f"链接提取 {n_ok}/{len(candidates)}", True, extract_elapsed)
                result["steps"].append({"step": "EXTRACT_LINKS", "action": f"链接 {n_ok}/{len(candidates)}", "elapsed_ms": extract_elapsed})

            # ── 6. 裁剪商品图片 ────────────────────────────────
            screenshot_path = self.ctx.result_screenshots[0] if self.ctx.result_screenshots else None
            if screenshot_path:
                self._crop_candidate_images(candidates, screenshot_path)

            # ── 7. 构建结果 ────────────────────────────────────
            result["candidates"] = [
                {
                    "position": c.position,
                    "title": c.title,
                    "price": str(c.price),
                    "sales_volume": c.sales_volume,
                    "shop_name": c.shop_name,
                    "image_url": c.image_url,
                    "product_url": c.product_url,
                    "pdd_goods_id": c.pdd_goods_id,
                }
                for c in candidates
            ]
            result["status"] = "success"
            result["total_elapsed_ms"] = int((time.monotonic() - overall_start) * 1000)

            logger.info("=" * 60)
            logger.info("流程执行成功！总耗时: %.1fs", result["total_elapsed_ms"] / 1000)
            logger.info("找到 %d 个候选商品", len(candidates))
            logger.info("=" * 60)

        except FlowError as e:
            result["status"] = "failed"
            result["error"] = {"code": e.code, "step": e.step, "message": e.message}
            result["total_elapsed_ms"] = int((time.monotonic() - overall_start) * 1000)
            logger.error("流程失败 [%s]: %s", e.step, e.message)

        except Exception as e:
            result["status"] = "failed"
            result["error"] = {"code": "EXECUTION_ERROR", "message": str(e)}
            result["total_elapsed_ms"] = int((time.monotonic() - overall_start) * 1000)
            logger.exception("执行异常: %s", e)

        finally:
            self._cleanup()

        return result

    def _log(self, step: str, action: str, success: bool, elapsed_ms: int = 0, message: str = ""):
        """打印步骤日志。"""
        status = "✓" if success else "✗"
        elapsed_str = f" [{elapsed_ms}ms]" if elapsed_ms else ""
        logger.info(f"  {status} {step}: {action}{elapsed_str}")
        if message and not success:
            logger.warning(f"    详情: {message}")

    def _download_image(self, url: str) -> Optional[str]:
        """下载图片到临时目录。"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.tiktok.com/",
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        }
        try:
            with httpx.Client(timeout=DOWNLOAD_TIMEOUT, follow_redirects=True, headers=headers) as client:
                resp = client.get(url)
                resp.raise_for_status()

            suffix = ".jpg"
            ct = resp.headers.get("content-type", "")
            if "png" in ct:
                suffix = ".png"
            elif "webp" in ct:
                suffix = ".webp"

            tmp = tempfile.NamedTemporaryFile(
                prefix="gp_pdd_test_",
                suffix=suffix,
                delete=False,
            )
            tmp.write(resp.content)
            tmp.close()
            logger.info("图片下载完成: %s (%d bytes)", tmp.name, len(resp.content))
            return tmp.name
        except Exception as e:
            logger.error("图片下载失败: %s — %s", url, e)
            return None

    def _crop_candidate_images(self, candidates: list, screenshot_path: str) -> None:
        """从结果页截图中裁剪商品主图。"""
        try:
            from PIL import Image
            import io as _io
        except ImportError:
            logger.warning("Pillow 未安装，跳过图片裁剪")
            return

        if not Path(screenshot_path).exists():
            return

        try:
            img = Image.open(screenshot_path)
        except Exception as e:
            logger.warning("截图打开失败: %s", e)
            return

        for c in candidates:
            if not c.image_bounds:
                continue
            x1, y1, x2, y2 = c.image_bounds
            if x2 <= x1 or y2 <= y1:
                continue
            try:
                cropped = img.crop((x1, y1, x2, y2))
                if cropped.mode in ("RGBA", "P", "LA"):
                    cropped = cropped.convert("RGB")

                buf = _io.BytesIO()
                cropped.save(buf, "JPEG", quality=90)
                img_bytes = buf.getvalue()

                # 保存到本地文件（不上传 OSS）
                output_path = self.artifacts.save_dir / f"product_img_{c.position}.jpg"
                output_path.write_bytes(img_bytes)
                c.image_url = str(output_path)
                logger.info("商品图片已裁剪: %s", output_path)
            except Exception as e:
                logger.warning("图片裁剪失败 pos=%d: %s", c.position, e)

    def _cleanup(self):
        """清理临时文件。"""
        if self.local_image and os.path.exists(self.local_image):
            try:
                os.remove(self.local_image)
            except Exception:
                pass

        # 清理云手机上的临时图片
        if self.ctx and self.ctx.remote_image_path:
            try:
                adb = AdbClient(serial=self.device_serial)
                adb.remove_remote_file(self.ctx.remote_image_path)
                adb.press_home()
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser(description="拍照购完整流程执行脚本")
    parser.add_argument("--task-id", type=int, default=0, help="任务 ID（从数据库取任务）")
    parser.add_argument("--device", type=str, help="设备序列号（如 emulator-5554）")
    parser.add_argument("--image-url", type=str, help="商品图片 URL")
    parser.add_argument("--local-image", type=str, help="本地图片路径")
    parser.add_argument("--max-candidates", type=int, default=4, help="最大候选商品数")
    parser.add_argument("--no-links", action="store_true", help="不提取商品链接")
    parser.add_argument("--user-id", type=int, help="用户 ID（用于设备调度）")
    parser.add_argument("--output", type=str, help="结果输出文件路径（JSON）")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细日志")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 如果指定了 task_id，从数据库加载任务信息
    if args.task_id > 0:
        db = SessionLocal()
        try:
            task = photo_search_service.get_task(db, args.task_id)
            if not task:
                logger.error("任务 #%d 不存在", args.task_id)
                sys.exit(1)

            product = db.query(Product).filter(Product.id == task.product_id).first()
            if not product:
                logger.error("商品 #%d 不存在", task.product_id)
                sys.exit(1)

            runner = FlowRunner(
                device_serial="",  # 将由设备调度分配
                task_id=args.task_id,
                source_image_url=task.source_image_url,
                max_candidates=getattr(task, "max_candidates", 4),
                fetch_pdd_links=getattr(task, "fetch_pdd_links", True),
                user_id=product.user_id,
            )

            # 调度设备
            mgr = DeviceManager(db)
            device = mgr.acquire_device(args.task_id, user_id=product.user_id)
            if not device:
                logger.error("无可用设备")
                sys.exit(1)

            runner.device_serial = device.device_id
            logger.info("已分配设备: %s", device.device_id)

            # 执行流程
            result = runner.run()

            # 释放设备
            mgr.release_device(device.device_id, success=result["status"] == "success")

        finally:
            db.close()
    else:
        # 直接模式：不需要数据库
        if not args.device:
            parser.error("--device 是必需的（除非使用 --task-id）")

        runner = FlowRunner(
            device_serial=args.device,
            task_id=args.task_id,
            source_image_url=args.image_url,
            local_image_path=args.local_image,
            max_candidates=args.max_candidates,
            fetch_pdd_links=not args.no_links,
        )

        result = runner.run()

    # 输出结果
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        logger.info("结果已保存到: %s", args.output)
    else:
        print("\n" + "=" * 60)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print("=" * 60)

    if result["status"] == "failed":
        sys.exit(1)


if __name__ == "__main__":
    main()
