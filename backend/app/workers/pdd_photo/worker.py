"""
拍照购 Worker —— 异步执行拍照购任务的入口。

由 FastAPI BackgroundTasks 调用，可后续迁移到 Celery / RQ。
核心职责：
1. 从任务表取任务
2. 调度设备
3. 下载商品图片
4. 执行拍照购状态机
5. 解析结果
6. 入库
7. 释放设备
"""
from __future__ import annotations

import logging
import os
import tempfile
import time
from pathlib import Path

import httpx

from app.config import get_settings
from app.database import SessionLocal
from app.services import photo_search_service
from .adb_client import AdbClient
from .link_extractor import fill_product_links_from_detail_taps
from .artifact_manager import ArtifactManager
from .device_manager import DeviceManager
from .pdd_photo_flow import FlowContext, FlowError, PddPhotoFlow
from .result_parser import ResultParser

logger = logging.getLogger(__name__)

DOWNLOAD_TIMEOUT = 30
MAX_CANDIDATES = 4


def execute_photo_search_task(task_id: int):
    """后台执行一个拍照购任务（线程安全，使用独立 DB session）。"""
    db = SessionLocal()
    device_serial = None
    local_image = None
    ctx = None
    artifacts = ArtifactManager(task_id)

    try:
        task = photo_search_service.get_task(db, task_id)
        if not task:
            logger.error("Task #%d not found", task_id)
            return
        if task.status != "queued":
            logger.warning("Task #%d status is %s, skip", task_id, task.status)
            return

        photo_search_service.update_task_status(db, task_id, "dispatching")

        # ── 1. 调度设备（云手机池 available + ADB，多任务 SKIP LOCKED 并行）──
        mgr = DeviceManager(db)
        device = mgr.acquire_device(task_id)

        if not device:
            photo_search_service.update_task_status(
                db, task_id, "failed",
                error_code="NO_DEVICE", error_message="无可用设备",
            )
            return

        device_serial = device.device_id
        photo_search_service.update_task_status(
            db, task_id, "running", device_id=device_serial,
        )

        # ── 2. 设备预热 ────────────────────────────────────────
        if not mgr.warm_up(device_serial):
            raise RuntimeError("设备预热失败")

        photo_search_service.save_action_log(
            db, task_id, device_serial, "PRECHECK", "设备预热完成",
        )

        # ── 3. 下载商品图片 ────────────────────────────────────
        local_image = _download_image(task.source_image_url, task_id)
        if not local_image:
            raise RuntimeError(f"图片下载失败: {task.source_image_url}")

        photo_search_service.save_action_log(
            db, task_id, device_serial, "DOWNLOAD", f"图片下载完成: {local_image}",
        )

        # ── 4. 执行拍照购流程 ──────────────────────────────────
        ctx = FlowContext(
            serial=device_serial,
            task_id=task_id,
            local_image_path=local_image,
            remote_image_filename=f"gp_pdd_{task_id}.jpg",
        )
        flow = PddPhotoFlow(ctx)

        try:
            step_logs = flow.execute()
        except FlowError as e:
            for sl in ctx.step_logs:
                photo_search_service.save_action_log(
                    db, task_id, device_serial,
                    step=sl.step, action=sl.action, success=sl.success,
                    elapsed_ms=sl.elapsed_ms,
                    screenshot_path=artifacts.save_screenshot(sl.screenshot_path, sl.step) if sl.screenshot_path else None,
                    xml_dump_path=artifacts.save_xml(sl.xml_path, sl.step) if sl.xml_path else None,
                    message=sl.message,
                )
            task_obj = photo_search_service.get_task(db, task_id)
            if task_obj:
                task_obj.attempt_count += 1
                db.commit()
            photo_search_service.update_task_status(
                db, task_id, "failed",
                error_code=e.code,
                error_message=(
                    f"拍照购流程失败 [{e.step.value}]: {e.message}"
                )[:2000],
            )
            return

        for sl in ctx.step_logs:
            photo_search_service.save_action_log(
                db, task_id, device_serial,
                step=sl.step, action=sl.action, success=sl.success,
                elapsed_ms=sl.elapsed_ms,
                screenshot_path=artifacts.save_screenshot(sl.screenshot_path, sl.step) if sl.screenshot_path else None,
                xml_dump_path=artifacts.save_xml(sl.xml_path, sl.step) if sl.xml_path else None,
                message=sl.message,
            )

        photo_search_service.update_task_status(db, task_id, "collecting")

        # ── 5. 解析结果 ────────────────────────────────────────
        photo_search_service.update_task_status(db, task_id, "parsing")

        xml_paths = []
        for p in ctx.result_xml_paths:
            saved = artifacts.save_xml(p, "result")
            xml_paths.append(saved or p)

        for p in ctx.result_screenshots:
            artifacts.save_screenshot(p, "result")

        parser = ResultParser()
        parse_result = parser.parse_xml_files(ctx.result_xml_paths)

        candidates = parse_result.candidates[:MAX_CANDIDATES]

        # ── 5a. 点进详情解析 goods_id → H5 商品链接（仍在结果页操作）──
        if get_settings().PDD_EXTRACT_PRODUCT_LINKS and candidates:
            adb_links = AdbClient(serial=device_serial)
            adb_links.kill_uiautomator()
            n_ok = fill_product_links_from_detail_taps(
                adb_links, candidates, max_items=MAX_CANDIDATES,
            )
            photo_search_service.save_action_log(
                db, task_id, device_serial, "EXTRACT_LINKS",
                f"商品链接解析成功 {n_ok}/{len(candidates)}",
            )

        # ── 5b. 从截图裁剪商品主图并上传 OSS ──────────────────
        screenshot_path = ctx.result_screenshots[0] if ctx.result_screenshots else None
        if screenshot_path:
            _crop_candidate_images(candidates, screenshot_path, task_id)

        raw_json = {
            "candidates": [
                {
                    "title": c.title,
                    "price": str(c.price),
                    "sales_volume": c.sales_volume,
                    "shop_name": c.shop_name,
                    "image_url": c.image_url,
                    "product_url": c.product_url,
                    "pdd_goods_id": c.pdd_goods_id,
                    "position": c.position,
                }
                for c in candidates
            ],
            "raw_texts_sample": parse_result.raw_texts[:50],
            "parse_errors": parse_result.parse_errors,
        }
        artifacts.save_result_json(raw_json, "parsed_candidates")

        photo_search_service.update_task_status(
            db, task_id, "saving",
            candidates_found=len(candidates),
            raw_result_json=raw_json,
        )

        # ── 6. 入库 ───────────────────────────────────────────
        saved_count = photo_search_service.save_candidates_to_matches(
            db, task.product_id, candidates,
        )

        # ── 7. 完成 ───────────────────────────────────────────
        task_obj = photo_search_service.get_task(db, task_id)
        task_obj.attempt_count += 1
        db.commit()

        photo_search_service.update_task_status(
            db, task_id, "success",
            candidates_saved=saved_count,
        )

        artifacts.save_step_logs(ctx.step_logs)
        logger.info(
            "Task #%d completed: %d candidates found, %d saved",
            task_id, len(candidates), saved_count,
        )

    except Exception as e:
        logger.exception("Task #%d failed: %s", task_id, e)
        try:
            task_obj = photo_search_service.get_task(db, task_id)
            if task_obj:
                task_obj.attempt_count += 1
                db.commit()

            photo_search_service.update_task_status(
                db, task_id, "failed",
                error_code="EXECUTION_ERROR",
                error_message=str(e)[:2000],
            )
        except Exception:
            logger.exception("Failed to update task status")

    finally:
        if device_serial:
            try:
                mgr = DeviceManager(db)
                task_obj = photo_search_service.get_task(db, task_id)
                success = task_obj and task_obj.status == "success"
                mgr.release_device(device_serial, success=success)

                adb = AdbClient(serial=device_serial)
                if ctx and ctx.remote_image_path:
                    adb.remove_remote_file(ctx.remote_image_path)
                adb.press_home()
            except Exception:
                logger.exception("Cleanup error for device %s", device_serial)

        try:
            db.close()
        except Exception:
            pass

        try:
            if local_image and os.path.exists(local_image):
                os.remove(local_image)
        except Exception:
            pass


def _crop_candidate_images(
    candidates: list,
    screenshot_path: str,
    task_id: int,
) -> None:
    """从结果页截图中按 bounds 裁剪每个候选商品的主图，上传到阿里云 OSS。"""
    try:
        from PIL import Image
        import io as _io
    except ImportError:
        logger.warning("Pillow not installed, skipping image crop")
        return

    if not Path(screenshot_path).exists():
        logger.warning("Screenshot not found: %s", screenshot_path)
        return

    try:
        img = Image.open(screenshot_path)
    except Exception as e:
        logger.warning("Failed to open screenshot: %s", e)
        return

    from app.services.oss_service import upload_image_bytes

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

            object_key = f"pdd_photo/task_{task_id}/product_img_{c.position}.jpg"
            oss_url = upload_image_bytes(img_bytes, object_key)
            if oss_url:
                c.image_url = oss_url
                logger.info("Uploaded product image pos=%d -> %s", c.position, oss_url)
            else:
                logger.warning("OSS upload returned None for pos=%d", c.position)
        except Exception as e:
            logger.warning("Failed to crop/upload image for position %d: %s", c.position, e)


def _download_image(url: str, task_id: int) -> str | None:
    """下载图片到临时目录，返回本地路径。"""
    if not url:
        return None
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
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
            prefix=f"gp_pdd_{task_id}_",
            suffix=suffix,
            delete=False,
        )
        tmp.write(resp.content)
        tmp.close()
        logger.info("Downloaded image to %s (%d bytes)", tmp.name, len(resp.content))
        return tmp.name
    except Exception as e:
        logger.error("Image download failed: %s — %s", url, e)
        return None
