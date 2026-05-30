"""
拍照购 Worker —— uiautomator2 版本。

与原版 worker.py 逻辑完全一致，
仅替换 pdd_photo 模块为 pdd_photo_u2 模块。
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
from app.models.product import Product
from app.services import photo_search_service
from .u2_client import U2Client
from .link_extractor_u2 import fill_product_links_from_detail_taps
from ..pdd_photo.artifact_manager import ArtifactManager
from ..pdd_photo.device_manager import DeviceManager
from ..pdd_photo.device_lock import DeviceLock
from ..pdd_photo.result_parser import ResultParser
from .pdd_photo_flow_u2 import FlowContext, FlowError, PddPhotoFlow

logger = logging.getLogger(__name__)

DOWNLOAD_TIMEOUT = 30
MAX_CANDIDATES = 4


def _task_max_candidates(task) -> int:
    raw = getattr(task, "max_candidates", None)
    if raw is None:
        return MAX_CANDIDATES
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return MAX_CANDIDATES
    return max(1, min(n, 50))


def execute_photo_search_task_u2(task_id: int):
    """后台执行一个拍照购任务（uiautomator2 版本）。"""
    db = SessionLocal()
    device_serial = None
    local_image = None
    ctx = None
    artifacts = ArtifactManager(task_id)
    device_lock = None
    _stop_heartbeat = None
    heartbeat_thread = None
    _redis_lock_acquired = False

    try:
        task = photo_search_service.get_task(db, task_id)
        if not task:
            logger.error("Task #%d not found", task_id)
            return
        if task.status != "queued":
            logger.warning("Task #%d status is %s, skip", task_id, task.status)
            return

        product_row = db.query(Product).filter(Product.id == task.product_id).first()
        if not product_row:
            photo_search_service.update_task_status(
                db, task_id, "failed",
                error_code="NO_PRODUCT", error_message="商品不存在，无法调度设备",
            )
            return

        photo_search_service.update_task_status(db, task_id, "dispatching")

        owner_user_id = product_row.user_id

        mgr = DeviceManager(db)
        device = mgr.acquire_device(task_id, user_id=owner_user_id)

        if not device:
            photo_search_service.update_task_status(
                db, task_id, "failed",
                error_code="NO_DEVICE", error_message="无可用设备",
            )
            return

        device_serial = device.device_id

        device_lock = DeviceLock(device_serial)
        if not device_lock.acquire(timeout=30):
            mgr.release_device(device_serial, success=False)
            photo_search_service.update_task_status(
                db, task_id, "failed",
                error_code="DEVICE_LOCKED", error_message="设备被其他任务占用，请稍后重试",
            )
            return
        _redis_lock_acquired = True

        import threading
        _stop_heartbeat = threading.Event()

        def _heartbeat_loop():
            while not _stop_heartbeat.is_set():
                _stop_heartbeat.wait(30)
                if not _stop_heartbeat.is_set():
                    try:
                        device_lock.heartbeat()
                    except Exception:
                        logger.warning("Device %s heartbeat failed", device_serial)

        heartbeat_thread = threading.Thread(target=_heartbeat_loop, daemon=True)
        heartbeat_thread.start()

        photo_search_service.update_task_status(
            db, task_id, "running", device_id=device_serial,
        )

        if not mgr.warm_up(device_serial):
            raise RuntimeError("设备预热失败")

        photo_search_service.save_action_log(
            db, task_id, device_serial, "PRECHECK", "设备预热完成",
        )

        local_image = _download_image(task.source_image_url, task_id)
        if not local_image:
            raise RuntimeError(f"图片下载失败: {task.source_image_url}")

        photo_search_service.save_action_log(
            db, task_id, device_serial, "DOWNLOAD", f"图片下载完成: {local_image}",
        )

        ctx = FlowContext(
            serial=device_serial,
            task_id=task_id,
            local_image_path=local_image,
            remote_image_filename=f"gp_pdd_u2_{task_id}.jpg",
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
        photo_search_service.update_task_status(db, task_id, "parsing")

        xml_paths = []
        for p in ctx.result_xml_paths:
            saved = artifacts.save_xml(p, "result")
            xml_paths.append(saved or p)

        for p in ctx.result_screenshots:
            artifacts.save_screenshot(p, "result")

        parser = ResultParser()
        parse_result = parser.parse_xml_files(ctx.result_xml_paths)

        cap = _task_max_candidates(task)
        candidates = parse_result.candidates[:cap]

        fetch_links = bool(getattr(task, "fetch_pdd_links", True))
        if fetch_links and get_settings().PDD_EXTRACT_PRODUCT_LINKS and candidates:
            client = U2Client(serial=device_serial)
            n_ok = fill_product_links_from_detail_taps(
                client, candidates, max_items=cap,
            )
            photo_search_service.save_action_log(
                db, task_id, device_serial, "EXTRACT_LINKS",
                f"商品链接解析成功 {n_ok}/{len(candidates)}",
            )

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

        saved_count = photo_search_service.save_candidates_to_matches(
            db, task.product_id, candidates,
        )

        task_obj = photo_search_service.get_task(db, task_id)
        task_obj.attempt_count += 1
        db.commit()

        photo_search_service.update_task_status(
            db, task_id, "success",
            candidates_saved=saved_count,
        )

        artifacts.save_step_logs(ctx.step_logs)
        logger.info(
            "Task #%d completed (u2): %d candidates found, %d saved",
            task_id, len(candidates), saved_count,
        )

    except Exception as e:
        logger.exception("Task #%d failed (u2): %s", task_id, e)
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
        if _stop_heartbeat is not None:
            _stop_heartbeat.set()
        if heartbeat_thread is not None:
            heartbeat_thread.join(timeout=2)

        if device_lock is not None and _redis_lock_acquired:
            try:
                device_lock.release()
            except Exception:
                logger.exception("Failed to release device lock for %s", device_serial)

        if device_serial:
            try:
                mgr = DeviceManager(db)
                task_obj = photo_search_service.get_task(db, task_id)
                success = task_obj and task_obj.status == "success"
                mgr.release_device(device_serial, success=success)
                logger.info("Device %s released (success=%s)", device_serial, success)

                client = U2Client(serial=device_serial)
                if ctx and ctx.remote_image_path:
                    client.remove_remote_file(ctx.remote_image_path)
                client.press_home()
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
            prefix=f"gp_pdd_u2_{task_id}_",
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
