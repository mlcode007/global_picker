"""
拼多多拍照购状态机 —— 完整的端到端执行流程。

状态迁移：
INIT -> PRECHECK -> PUSH_IMAGE -> SEND_IMAGE_TO_PDD
-> WAIT_RESULT -> COLLECT_RESULT -> DONE

核心策略：通过 android.intent.action.SEND 将图片直接分享给
PDD 的 AppLinkActivity，PDD 收到后自动执行「搜图片同款」，
完全绕过相机页面和相册权限问题。
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Optional

from .adb_client import AdbClient
from .page_detector import PageDetector, PageInfo, PageType

logger = logging.getLogger(__name__)

PDD_PACKAGE = "com.xunmeng.pinduoduo"


class FlowStep(str, Enum):
    INIT = "INIT"
    PRECHECK = "PRECHECK"
    PUSH_IMAGE = "PUSH_IMAGE"
    SEND_IMAGE_TO_PDD = "SEND_IMAGE_TO_PDD"
    WAIT_RESULT = "WAIT_RESULT"
    COLLECT_RESULT = "COLLECT_RESULT"
    DONE = "DONE"
    ERROR = "ERROR"


class FlowError(Exception):
    def __init__(self, step: FlowStep, code: str, message: str):
        self.step = step
        self.code = code
        self.message = message
        super().__init__(f"[{step.value}] {code}: {message}")


@dataclass
class StepLog:
    step: str
    action: str
    success: bool
    elapsed_ms: int = 0
    screenshot_path: Optional[str] = None
    xml_path: Optional[str] = None
    message: str = ""


@dataclass
class FlowContext:
    serial: str
    task_id: int
    local_image_path: str
    remote_image_filename: str = ""
    remote_image_path: str = ""
    result_xml_paths: list[str] = field(default_factory=list)
    result_screenshots: list[str] = field(default_factory=list)
    step_logs: list[StepLog] = field(default_factory=list)
    current_step: FlowStep = FlowStep.INIT
    max_retries_per_step: int = 2
    screen_w: int = 1080
    screen_h: int = 2400


class PddPhotoFlow:
    """拍照购自动化主流程。"""

    def __init__(self, ctx: FlowContext):
        self.ctx = ctx
        self.adb = AdbClient(serial=ctx.serial)
        self.detector = PageDetector(self.adb)

    def execute(self) -> list[StepLog]:
        """执行完整流程，返回步骤日志列表。"""
        steps: list[tuple[FlowStep, Callable]] = [
            (FlowStep.PRECHECK, self._precheck),
            (FlowStep.PUSH_IMAGE, self._push_image),
            (FlowStep.SEND_IMAGE_TO_PDD, self._send_image_to_pdd),
            (FlowStep.WAIT_RESULT, self._wait_result),
            (FlowStep.COLLECT_RESULT, self._collect_result),
        ]

        for step_enum, step_fn in steps:
            self.ctx.current_step = step_enum
            retries = 0
            while retries <= self.ctx.max_retries_per_step:
                t0 = time.monotonic()
                try:
                    step_fn()
                    elapsed = int((time.monotonic() - t0) * 1000)
                    shot = self.adb.screenshot(tag=step_enum.value)
                    self.ctx.step_logs.append(StepLog(
                        step=step_enum.value,
                        action=f"{step_enum.value} completed",
                        success=True,
                        elapsed_ms=elapsed,
                        screenshot_path=shot,
                    ))
                    break
                except FlowError:
                    raise
                except Exception as e:
                    elapsed = int((time.monotonic() - t0) * 1000)
                    shot = self.adb.screenshot(tag=f"{step_enum.value}_err")
                    self.ctx.step_logs.append(StepLog(
                        step=step_enum.value,
                        action=f"{step_enum.value} attempt {retries + 1} failed",
                        success=False,
                        elapsed_ms=elapsed,
                        screenshot_path=shot,
                        message=str(e),
                    ))
                    retries += 1
                    if retries > self.ctx.max_retries_per_step:
                        raise FlowError(step_enum, "STEP_FAILED", str(e))
                    logger.warning("Step %s retry %d: %s", step_enum.value, retries, e)
                    time.sleep(1)

        self.ctx.current_step = FlowStep.DONE
        return self.ctx.step_logs

    # ── 各步骤实现 ────────────────────────────────────────────

    def _precheck(self):
        if not self.adb.is_connected():
            raise FlowError(FlowStep.PRECHECK, "DEVICE_DISCONNECTED", "设备未连接")

        self.adb.ensure_screen_on()
        self.adb.disable_animations()

        w, h = self.adb.screen_size()
        self.ctx.screen_w = w
        self.ctx.screen_h = h
        logger.info("Screen size: %dx%d", w, h)

        if not self.adb.is_app_installed(PDD_PACKAGE):
            raise FlowError(FlowStep.PRECHECK, "APP_NOT_INSTALLED", "拼多多未安装")

        for perm in [
            "android.permission.READ_EXTERNAL_STORAGE",
            "android.permission.WRITE_EXTERNAL_STORAGE",
            "android.permission.CAMERA",
        ]:
            self.adb.shell(f"pm grant {PDD_PACKAGE} {perm}")
        logger.info("Granted storage/camera permissions to PDD")

    def _push_image(self):
        import os
        if not os.path.exists(self.ctx.local_image_path):
            raise FlowError(FlowStep.PUSH_IMAGE, "IMAGE_NOT_FOUND", "本地图片不存在")

        filename = self.ctx.remote_image_filename or f"gp_pdd_{self.ctx.task_id}.jpg"
        self.ctx.remote_image_filename = filename
        self.ctx.remote_image_path = self.adb.push_image_to_gallery(
            self.ctx.local_image_path, filename
        )
        time.sleep(1)

    def _send_image_to_pdd(self):
        """通过 Intent SEND 将图片直接分享给 PDD 的 AppLinkActivity。

        PDD 收到图片后会自动进入「搜图片同款」页面，完全绕过
        相机页面、相册选择和文件权限问题。
        """
        remote_path = self.ctx.remote_image_path
        if not remote_path:
            raise FlowError(FlowStep.SEND_IMAGE_TO_PDD, "NO_IMAGE",
                            "没有已推送的图片路径")

        content_id = self.adb.get_media_content_id(remote_path)
        if not content_id:
            logger.warning("MediaStore ID not found, triggering rescan")
            self.adb.shell(
                f"am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE "
                f"-d file://{remote_path}"
            )
            time.sleep(2)
            content_id = self.adb.get_media_content_id(remote_path)

        if not content_id:
            raise FlowError(FlowStep.SEND_IMAGE_TO_PDD, "MEDIA_NOT_FOUND",
                            f"图片未出现在 MediaStore: {remote_path}")

        content_uri = f"content://media/external/images/media/{content_id}"
        send_cmd = (
            f"am start -a android.intent.action.SEND -t image/jpeg "
            f"--grant-read-uri-permission "
            f"-n {PDD_PACKAGE}/.splash.link.AppLinkActivity "
            f"--eu android.intent.extra.STREAM {content_uri}"
        )
        result = self.adb.shell(send_cmd)
        logger.info("Sent image to PDD via Intent SEND: %s (content_id=%s)",
                     result.stdout.strip(), content_id)
        time.sleep(3)

        for attempt in range(5):
            pkg, act = self.adb.current_activity()
            if pkg == PDD_PACKAGE:
                logger.info("PDD is in foreground: %s", act)
                return
            time.sleep(2)

        raise FlowError(FlowStep.SEND_IMAGE_TO_PDD, "PDD_NOT_FOREGROUND",
                        "分享图片后 PDD 未进入前台")

    def _wait_result(self):
        """等待拍照购结果页加载完成。"""
        self.adb.kill_uiautomator()

        for i in range(20):
            time.sleep(1.5)

            pkg, act = self.adb.current_activity()
            if pkg != PDD_PACKAGE:
                if self._check_and_handle_permission_by_activity():
                    continue
                self.adb.press_back()
                continue

            xml = self.adb.dump_ui_xml(tag=f"wait_result_{i}", timeout=5)
            if not xml:
                logger.debug("wait_result %d: dump failed, retrying", i)
                self.adb.kill_uiautomator()
                continue

            texts = self.detector._extract_texts(xml)
            joined = " ".join(texts)

            if "尺寸过小" in joined or "图片过小" in joined:
                logger.warning("PDD rejected image: too small")
                raise FlowError(FlowStep.WAIT_RESULT, "IMAGE_TOO_SMALL",
                                "PDD 提示图片尺寸过小，请使用更大分辨率的图片")

            page = self._quick_classify_xml(xml, pkg, act)

            if page.page_type == PageType.PDD_DIALOG:
                self._dismiss_dialog(page)
                continue

            if page.page_type == PageType.PERMISSION_DIALOG:
                self._grant_permission(page)
                continue

            if page.page_type == PageType.PDD_PHOTO_RESULT:
                logger.info("Result page detected after %d iterations", i + 1)
                time.sleep(1)
                return

            price_nodes = self.detector.find_nodes_by_text(xml, ["¥"])
            if len(price_nodes) >= 2:
                logger.info("Price nodes detected (%d), treating as result page", len(price_nodes))
                time.sleep(1)
                return

            if "搜图片同款" in joined:
                logger.info("Found '搜图片同款' title, result page loaded")
                time.sleep(1)
                return

            if "正在识别" in joined or "正在搜索" in joined:
                logger.debug("wait_result %d: PDD is processing...", i)
                continue

        raise FlowError(FlowStep.WAIT_RESULT, "RESULT_TIMEOUT", "等待结果页超时 30s")

    def _collect_result(self):
        """采集结果页内容：仅截取当前屏幕（前几个商品），不滚动。"""
        self.adb.kill_uiautomator()

        # 只采集首屏，拿前 4 个商品即可
        tag = "result_page_0"
        xml_path = self.adb.dump_ui_xml(tag=tag, timeout=6)
        shot = self.adb.screenshot(tag=tag)

        if xml_path:
            self.ctx.result_xml_paths.append(xml_path)
        if shot:
            self.ctx.result_screenshots.append(shot)

        # ── 如需采集更多商品，取消以下注释启用滚动采集 ──
        # for scroll in range(1, 3):
        #     self.adb.scroll_down(800)
        #     time.sleep(1.5)
        #     tag = f"result_page_{scroll}"
        #     xml_path = self.adb.dump_ui_xml(tag=tag, timeout=6)
        #     shot = self.adb.screenshot(tag=tag)
        #     if xml_path:
        #         self.ctx.result_xml_paths.append(xml_path)
        #     if shot:
        #         self.ctx.result_screenshots.append(shot)

        if not self.ctx.result_xml_paths:
            raise FlowError(FlowStep.COLLECT_RESULT, "NO_RESULT_DATA", "未采集到任何结果数据")

    # ── 辅助方法 ──────────────────────────────────────────────

    def _has_left_camera_page(self) -> bool:
        """判断是否已离开相机页面（不使用 uiautomator，避免卡死）。"""
        pkg, act = self.adb.current_activity()

        if pkg != PDD_PACKAGE:
            return True

        # PDD 内部跳转不会改变 package，尝试快速 dump 测试（短超时）
        xml = self.adb.dump_ui_xml(tag="left_camera_check", timeout=3)
        if xml:
            return True
        return False

    def _check_and_handle_permission_by_activity(self) -> bool:
        """用 Activity 名检测并处理系统权限弹窗，不依赖 uiautomator。"""
        pkg, act = self.adb.current_activity()
        act_lower = act.lower()

        if not ("permission" in act_lower or "grant" in act_lower
                or "packageinstaller" in pkg.lower()):
            return False

        logger.info("Permission dialog detected via activity: %s/%s", pkg, act)
        xml = self.adb.dump_ui_xml(tag="perm_dialog", timeout=5)
        if xml:
            allow_btn = self.detector.find_node_by_text(
                xml, ["始终允许", "仅在使用中允许", "允许", "仅此一次"]
            )
            if allow_btn:
                self.adb.tap(*allow_btn["center"])
                time.sleep(1)
                return True

        w, h = self.ctx.screen_w, self.ctx.screen_h
        self.adb.tap(w // 2, h * 70 // 100)
        time.sleep(1)
        return True

    def _quick_classify_xml(self, xml_path: str, pkg: str, act: str) -> PageInfo:
        """在已有 XML 的基础上快速分类页面（不再额外 dump）。"""
        texts = self.detector._extract_texts(xml_path)

        if self.detector._has_permission_dialog(texts):
            return PageInfo(PageType.PERMISSION_DIALOG, pkg, act, xml_path, texts)

        if self.detector._has_dialog(texts):
            return PageInfo(PageType.PDD_DIALOG, pkg, act, xml_path, texts)

        page_type = self.detector._classify_page(texts, act)
        return PageInfo(page_type, pkg, act, xml_path, texts)

    def _wait_for_package(self, package: str, timeout: int = 8):
        for _ in range(timeout * 2):
            time.sleep(0.5)
            if self.adb.current_package() == package:
                return
        raise FlowError(FlowStep.START_APP, "APP_START_TIMEOUT", f"{package} 启动超时")

    def _dismiss_dialog(self, page: PageInfo):
        if not page.xml_path:
            self.adb.press_back()
            return
        close_btn = self.detector.find_node_by_text(
            page.xml_path, ["知道了", "我知道了", "关闭", "取消", "以后再说", "暂不", "下次再说"]
        )
        if close_btn:
            self.adb.tap(*close_btn["center"])
        else:
            self.adb.press_back()
        time.sleep(0.5)

    def _grant_permission(self, page: PageInfo):
        if not page.xml_path:
            xml_path = self.adb.dump_ui_xml(tag="permission")
        else:
            xml_path = page.xml_path
        if xml_path:
            allow_btn = self.detector.find_node_by_text(
                xml_path, ["始终允许", "仅在使用中允许", "允许", "仅此一次"]
            )
            if allow_btn:
                self.adb.tap(*allow_btn["center"])
                time.sleep(0.5)
                return
        w, h = self.ctx.screen_w, self.ctx.screen_h
        self.adb.tap(w // 2, h * 67 // 100)
        time.sleep(0.5)
