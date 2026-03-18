"""
ADB 客户端封装 —— 所有与 Android 设备的底层交互在此处完成。

职责：
- shell 命令执行
- push / pull 文件
- 截图
- UI XML dump
- 点击、滑动、按键输入
- 当前 Activity / 包名查询
- 屏幕唤醒与解锁
"""
from __future__ import annotations

import logging
import os
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

ARTIFACTS_DIR = Path(tempfile.gettempdir()) / "gp_pdd_artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class AdbResult:
    returncode: int
    stdout: str
    stderr: str
    elapsed_ms: int = 0

    @property
    def ok(self) -> bool:
        return self.returncode == 0


@dataclass
class AdbClient:
    serial: str
    adb_bin: str = "adb"
    timeout: int = 30
    _connected: bool = False

    def ensure_connected(self):
        """对网络设备（host:port 格式）自动执行 adb connect。"""
        if self._connected:
            return
        if ":" in self.serial:
            r = self._run(["connect", self.serial], timeout=10)
            if "connected" in r.stdout.lower() or "already" in r.stdout.lower():
                logger.info("ADB connected to %s", self.serial)
            else:
                logger.warning("ADB connect to %s: %s %s", self.serial, r.stdout, r.stderr)
        self._connected = True

    def _run(self, args: list[str], timeout: int | None = None) -> AdbResult:
        if args[0] != "connect":
            self.ensure_connected()
        if args[0] == "connect":
            cmd = [self.adb_bin] + args
        else:
            cmd = [self.adb_bin, "-s", self.serial] + args
        t0 = time.monotonic()
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout or self.timeout,
            )
            elapsed = int((time.monotonic() - t0) * 1000)
            return AdbResult(proc.returncode, proc.stdout.strip(), proc.stderr.strip(), elapsed)
        except subprocess.TimeoutExpired:
            elapsed = int((time.monotonic() - t0) * 1000)
            logger.warning("ADB command timeout: %s", " ".join(cmd))
            return AdbResult(-1, "", "timeout", elapsed)

    # ── 基础命令 ──────────────────────────────────────────────

    def shell(self, cmd: str, timeout: int | None = None) -> AdbResult:
        return self._run(["shell", cmd], timeout=timeout)

    def push(self, local_path: str, remote_path: str) -> AdbResult:
        return self._run(["push", local_path, remote_path], timeout=60)

    def pull(self, remote_path: str, local_path: str) -> AdbResult:
        return self._run(["pull", remote_path, local_path], timeout=60)

    def get_state(self) -> str:
        r = self._run(["get-state"], timeout=5)
        return r.stdout if r.ok else "unknown"

    def is_connected(self) -> bool:
        return self.get_state() == "device"

    # ── 屏幕控制 ──────────────────────────────────────────────

    def wake_screen(self) -> AdbResult:
        state = self.shell("dumpsys power | grep 'Display Power'")
        if "state=OFF" in state.stdout:
            self.shell("input keyevent KEYCODE_WAKEUP")
            time.sleep(0.5)
        return self.shell("input keyevent KEYCODE_MENU")

    def unlock_screen(self) -> AdbResult:
        w, h = self.screen_size()
        cx = w // 2
        return self.shell(f"input swipe {cx} {h * 5 // 6} {cx} {h // 3} 300")

    def ensure_screen_on(self):
        self.wake_screen()
        time.sleep(0.3)
        self.unlock_screen()
        time.sleep(0.3)

    # ── 交互操作 ──────────────────────────────────────────────

    def tap(self, x: int, y: int) -> AdbResult:
        return self.shell(f"input tap {x} {y}")

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> AdbResult:
        return self.shell(f"input swipe {x1} {y1} {x2} {y2} {duration_ms}")

    def scroll_down(self, distance: int = 0) -> AdbResult:
        w, h = self.screen_size()
        cx = w // 2
        d = distance if distance else h // 3
        start_y = h // 2 + d // 2
        end_y = h // 2 - d // 2
        return self.swipe(cx, start_y, cx, end_y, 400)

    def scroll_up(self, distance: int = 0) -> AdbResult:
        w, h = self.screen_size()
        cx = w // 2
        d = distance if distance else h // 3
        start_y = h // 2 - d // 2
        end_y = h // 2 + d // 2
        return self.swipe(cx, start_y, cx, end_y, 400)

    def keyevent(self, code: str) -> AdbResult:
        return self.shell(f"input keyevent {code}")

    def press_back(self) -> AdbResult:
        return self.keyevent("KEYCODE_BACK")

    def press_home(self) -> AdbResult:
        return self.keyevent("KEYCODE_HOME")

    def input_text(self, text: str) -> AdbResult:
        escaped = text.replace(" ", "%s").replace("'", "\\'")
        return self.shell(f"input text '{escaped}'")

    # ── 截图与 UI dump ────────────────────────────────────────

    def screenshot(self, tag: str = "") -> Optional[str]:
        """截图保存到本地，返回本地路径"""
        ts = int(time.time() * 1000)
        remote = f"/sdcard/gp_screen_{ts}.png"
        local = str(ARTIFACTS_DIR / f"screen_{tag}_{ts}.png")

        r1 = self.shell(f"screencap -p {remote}", timeout=10)
        if not r1.ok:
            logger.error("screencap failed: %s", r1.stderr)
            return None

        r2 = self.pull(remote, local)
        self.shell(f"rm {remote}")

        if r2.ok and os.path.exists(local):
            return local
        return None

    def kill_uiautomator(self):
        """强制结束设备上残留的 uiautomator 进程，防止后续 dump 卡死。"""
        self.shell("kill $(pidof uiautomator) 2>/dev/null", timeout=3)
        time.sleep(0.3)

    def dump_ui_xml(self, tag: str = "", timeout: int = 8) -> Optional[str]:
        """dump 当前界面 XML，返回本地路径。超时后自动清理孤儿进程。"""
        ts = int(time.time() * 1000)
        remote = "/sdcard/gp_ui_dump.xml"
        local = str(ARTIFACTS_DIR / f"ui_{tag}_{ts}.xml")

        r1 = self.shell(f"uiautomator dump {remote}", timeout=timeout)
        if not r1.ok and "dump" not in r1.stdout.lower():
            if r1.stderr == "timeout":
                self.kill_uiautomator()
            logger.error("uiautomator dump failed: %s", r1.stderr)
            return None

        r2 = self.pull(remote, local)
        self.shell(f"rm {remote}")

        if r2.ok and os.path.exists(local):
            return local
        return None

    # ── App 管理 ───────────────────────────────────────────────

    def current_activity(self) -> Tuple[str, str]:
        """返回 (package, activity)"""
        r = self.shell("dumpsys activity activities | grep -E 'mResumedActivity|topResumedActivity'")
        m = re.search(r"([a-zA-Z0-9_.]+)/([a-zA-Z0-9_.]+)", r.stdout)
        if m:
            return m.group(1), m.group(2)
        return "", ""

    def current_package(self) -> str:
        pkg, _ = self.current_activity()
        return pkg

    def start_app(self, package: str) -> AdbResult:
        return self.shell(
            f"monkey -p {package} -c android.intent.category.LAUNCHER 1"
        )

    def force_stop(self, package: str) -> AdbResult:
        return self.shell(f"am force-stop {package}")

    def clear_app_data(self, package: str) -> AdbResult:
        return self.shell(f"pm clear {package}")

    def is_app_installed(self, package: str) -> bool:
        r = self.shell(f"pm list packages {package}")
        return package in r.stdout

    # ── 文件与媒体 ─────────────────────────────────────────────

    def push_image_to_gallery(self, local_path: str, remote_filename: str) -> str:
        """推送图片到设备相册目录并触发媒体扫描，返回设备端路径"""
        remote_dir = "/sdcard/DCIM/Camera"
        remote_path = f"{remote_dir}/{remote_filename}"
        self.shell(f"mkdir -p {remote_dir}")
        self.push(local_path, remote_path)
        self.shell(
            f"am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE "
            f"-d file://{remote_path}"
        )
        time.sleep(1)
        return remote_path

    def remove_remote_file(self, remote_path: str) -> AdbResult:
        return self.shell(f"rm -f {remote_path}")

    def get_media_content_id(self, remote_path: str) -> Optional[str]:
        """查询 MediaStore 获取指定文件的 content ID，用于构造 content:// URI"""
        storage_path = remote_path.replace("/sdcard/", "/storage/emulated/0/")
        r = self.shell(
            f"content query --uri content://media/external/images/media "
            f"--projection _id --sort '_id DESC'"
        )
        for line in r.stdout.splitlines():
            if "_id=" in line:
                m = re.search(r"_id=(\d+)", line)
                if m:
                    cid = m.group(1)
                    detail = self.shell(
                        f"content query --uri content://media/external/images/media/{cid} "
                        f"--projection _data"
                    )
                    if storage_path in detail.stdout:
                        return cid
        return None

    # ── 设备信息 ───────────────────────────────────────────────

    def screen_size(self) -> Tuple[int, int]:
        r = self.shell("wm size")
        m = re.search(r"(\d+)x(\d+)", r.stdout)
        if m:
            return int(m.group(1)), int(m.group(2))
        return 1080, 2400

    def battery_level(self) -> int:
        r = self.shell("dumpsys battery | grep level")
        m = re.search(r"(\d+)", r.stdout)
        return int(m.group(1)) if m else -1

    def disable_animations(self):
        for anim in ["window_animation_scale", "transition_animation_scale", "animator_duration_scale"]:
            self.shell(f"settings put global {anim} 0")

    def set_screen_timeout(self, ms: int = 1800000):
        self.shell(f"settings put system screen_off_timeout {ms}")
