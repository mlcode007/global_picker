"""
拍照购完整流程脚本 —— uiautomator2 版本。

使用方式：
  # 直接指定图片和设备执行
  python -m app.workers.pdd_photo_u2.run_flow_u2 \
    --device emulator-5554 \
    --image-url "https://example.com/product.jpg"

  # 使用本地图片文件
  python -m app.workers.pdd_photo_u2.run_flow_u2 \
    --device emulator-5554 \
    --local-image /tmp/test.jpg

  # 不提取商品链接（更快）
  python -m app.workers.pdd_photo_u2.run_flow_u2 \
    --device emulator-5554 \
    --image-url "https://example.com/product.jpg" \
    --no-links

  # 保存结果到 JSON
  python -m app.workers.pdd_photo_u2.run_flow_u2 \
    --device emulator-5554 \
    --image-url "https://example.com/product.jpg" \
    --output result.json

  # 详细日志
  python -m app.workers.pdd_photo_u2.run_flow_u2 \
    --device emulator-5554 \
    --image-url "https://example.com/product.jpg" \
    -v
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

from app.workers.pdd_photo_u2.u2_client import U2Client
from app.workers.pdd_photo_u2.link_extractor_u2 import fill_product_links_from_detail_taps
from app.workers.pdd_photo.artifact_manager import ArtifactManager
from app.workers.pdd_photo.result_parser import ResultParser
from app.workers.pdd_photo_u2.pdd_photo_flow_u2 import FlowContext, FlowError, PddPhotoFlow

logger = logging.getLogger("pdd_photo_flow_u2")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

DOWNLOAD_TIMEOUT = 30


class FlowRunner:
    """拍照购流程执行器（uiautomator2 版本）。"""

    def __init__(
        self,
        device_serial: str,
        task_id: int = 0,
        source_image_url: Optional[str] = None,
        local_image_path: Optional[str] = None,
        max_candidates: int = 4,
        fetch_pdd_links: bool = True,
    ):
        self.device_serial = device_serial
        self.task_id = task_id
        self.source_image_url = source_image_url
        self.local_image_path = local_image_path
        self.max_candidates = max_candidates
        self.fetch_pdd_links = fetch_pdd_links

        self.artifacts = ArtifactManager(task_id)
        self.step_logs: list = []
        self.local_image: Optional[str] = None
        self.ctx: Optional[FlowContext] = None

    def run(self) -> dict:
        overall_start = time.monotonic()
        result = {
            "task_id": self.task_id,
            "device_serial": self.device_serial,
            "version": "uiautomator2",
            "status": "running",
            "steps": [],
            "candidates": [],
            "total_elapsed_ms": 0,
            "error": None,
        }

        try:
            # ── 1. 设备预热 ────────────────────────────────────
            t0 = time.monotonic()
            client = U2Client(serial=self.device_serial)
            if not client.is_connected():
                raise RuntimeError("设备未连接")
            client.ensure_screen_on()
            client.disable_animations()
            client.press_home()
            time.sleep(0.3)
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
                remote_image_filename=f"gp_pdd_u2_{self.task_id or 'test'}.jpg",
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

            # ── 4. 解析结果 ───────────────────────────────────
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
            if self.fetch_pdd_links and candidates:
                t0 = time.monotonic()
                n_ok = fill_product_links_from_detail_taps(client, candidates, max_items=cap)
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
        status = "✓" if success else "✗"
        elapsed_str = f" [{elapsed_ms}ms]" if elapsed_ms else ""
        logger.info(f"  {status} {step}: {action}{elapsed_str}")
        if message and not success:
            logger.warning(f"    详情: {message}")

    def _download_image(self, url: str) -> Optional[str]:
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
                prefix="gp_pdd_u2_test_",
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

                output_path = self.artifacts.results_dir / f"product_img_{c.position}.jpg"
                output_path.write_bytes(img_bytes)
                c.image_url = str(output_path)
                logger.info("商品图片已裁剪: %s", output_path)
            except Exception as e:
                logger.warning("图片裁剪失败 pos=%d: %s", c.position, e)

    def _cleanup(self):
        if self.local_image and os.path.exists(self.local_image):
            try:
                os.remove(self.local_image)
            except Exception:
                pass

        if self.ctx and self.ctx.remote_image_path:
            try:
                client = U2Client(serial=self.device_serial)
                client.remove_remote_file(self.ctx.remote_image_path)
                client.press_home()
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser(description="拍照购完整流程执行脚本（uiautomator2 版本）")
    parser.add_argument("--device", type=str, required=True, help="设备序列号（如 emulator-5554）")
    parser.add_argument("--image-url", type=str, help="商品图片 URL")
    parser.add_argument("--local-image", type=str, help="本地图片路径")
    parser.add_argument("--max-candidates", type=int, default=4, help="最大候选商品数")
    parser.add_argument("--no-links", action="store_true", help="不提取商品链接")
    parser.add_argument("--output", type=str, help="结果输出文件路径（JSON）")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细日志")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    runner = FlowRunner(
        device_serial=args.device,
        task_id=0,
        source_image_url=args.image_url,
        local_image_path=args.local_image,
        max_candidates=args.max_candidates,
        fetch_pdd_links=not args.no_links,
    )

    result = runner.run()

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
