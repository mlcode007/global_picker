"""
uiautomator2 客户端封装 —— 替代 adb_client.py，使用 uiautomator2 库。

职责：
- 截图（uiautomator2 原生优化）
- UI XML dump（hierarchy）
- 点击、滑动、按键输入
- 当前 Activity / 包名查询
- 屏幕唤醒与解锁
- 文件 push/pull（仍用 adb）
- 媒体扫描与 MediaStore 查询（仍用 adb shell）
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

import uiautomator2 as u2

logger = logging.getLogger(__name__)

ARTIFACTS_DIR = Path(tempfile.gettempdir()) / "gp_pdd_artifacts_u2"
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
class U2Client:
    serial: str
    adb_bin: str = "adb"
    timeout: int = 30
    _device = None
    _connected: bool = False

    @property
    def device(self):
        if self._device is None:
            self.ensure_connected()
        return self._device

    def ensure_connected(self):
        if self._connected and self._device is not None:
            try:
                self._device.info
                return
            except Exception:
                self._device = None
                self._connected = False

        if ":" in self.serial:
            host, port = self.serial.rsplit(":", 1)
            try:
                port = int(port)
            except ValueError:
                host, port = self.serial, 5555
            self._device = u2.connect(host, port)
        else:
            self._device = u2.connect(self.serial)

        self._connected = True
        logger.info("U2 connected to %s", self.serial)

    def _run_adb(self, args: list[str], timeout: int | None = None) -> AdbResult:
        """执行原生 adb 命令（用于 push/pull/media 等 u2 不覆盖的操作）。"""
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
            return AdbResult(-1, "", "timeout", elapsed)

    # ── 基础命令 ──────────────────────────────────────────────

    def shell(self, cmd: str, timeout: int | None = None) -> AdbResult:
        return self._run_adb(["shell", cmd], timeout=timeout)

    def push(self, local_path: str, remote_path: str) -> AdbResult:
        return self._run_adb(["push", local_path, remote_path], timeout=30)

    def pull(self, remote_path: str, local_path: str, timeout: int = 15) -> AdbResult:
        return self._run_adb(["pull", remote_path, local_path], timeout=timeout)

    def get_state(self) -> str:
        r = self._run_adb(["get-state"], timeout=5)
        return r.stdout if r.ok else "unknown"

    def is_connected(self) -> bool:
        try:
            self.ensure_connected()
            self._device.info
            return True
        except Exception:
            return False

    # ── 屏幕控制 ──────────────────────────────────────────────

    def wake_screen(self) -> AdbResult:
        try:
            info = self.device.info
            if not info.get("screenOn", True):
                self.device.screen_on()
                time.sleep(0.3)
            return AdbResult(0, "ok", "", 0)
        except Exception as e:
            return AdbResult(1, "", str(e), 0)

    def unlock_screen(self) -> AdbResult:
        try:
            w, h = self.screen_size()
            self.device.swipe(w // 2, h * 5 // 6, w // 2, h // 3, duration=0.3)
            return AdbResult(0, "ok", "", 0)
        except Exception as e:
            return AdbResult(1, "", str(e), 0)

    def ensure_screen_on(self):
        self.wake_screen()
        time.sleep(0.2)
        self.unlock_screen()
        time.sleep(0.2)

    # ── 交互操作 ──────────────────────────────────────────────

    def tap(self, x: int, y: int) -> AdbResult:
        try:
            self.device.click(x, y)
            return AdbResult(0, "ok", "", 0)
        except Exception as e:
            return AdbResult(1, "", str(e), 0)

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> AdbResult:
        try:
            self.device.swipe(x1, y1, x2, y2, duration=duration_ms / 1000.0)
            return AdbResult(0, "ok", "", 0)
        except Exception as e:
            return AdbResult(1, "", str(e), 0)

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
        try:
            self.device.press(code.replace("KEYCODE_", ""))
            return AdbResult(0, "ok", "", 0)
        except Exception as e:
            return AdbResult(1, "", str(e), 0)

    def press_back(self) -> AdbResult:
        return self.keyevent("KEYCODE_BACK")

    def press_home(self) -> AdbResult:
        return self.keyevent("KEYCODE_HOME")

    def input_text(self, text: str) -> AdbResult:
        try:
            self.device.send_keys(text)
            return AdbResult(0, "ok", "", 0)
        except Exception as e:
            return AdbResult(1, "", str(e), 0)

    # ── 截图与 UI dump ────────────────────────────────────────

    def screenshot(self, tag: str = "") -> Optional[str]:
        """截图保存到本地，返回本地路径。

        uiautomator2 原生截图，内部已优化，通常比 screencap→pull 快。
        """
        ts = int(time.time() * 1000)
        local = str(ARTIFACTS_DIR / f"screen_{tag}_{ts}.png")
        try:
            self.ensure_connected()
            self.device.screenshot(local)
            if os.path.exists(local) and os.path.getsize(local) > 0:
                return local
        except Exception as e:
            logger.error("u2 screenshot failed: %s", e)
        return None

    def kill_uiautomator(self):
        """uiautomator2 不需要手动 kill，但保留接口兼容。"""
        pass

    def dump_ui_xml(self, tag: str = "", timeout: int = 5) -> Optional[str]:
        """dump 当前界面 XML，返回本地路径。

        使用 uiautomator2 的 dump_hierarchy()，比 uiautomator dump 更快更稳定。
        """
        ts = int(time.time() * 1000)
        local = str(ARTIFACTS_DIR / f"ui_{tag}_{ts}.xml")
        try:
            self.ensure_connected()
            xml = self.device.dump_hierarchy()
            with open(local, "w", encoding="utf-8") as f:
                f.write(xml)
            if os.path.exists(local) and os.path.getsize(local) > 0:
                return local
        except Exception as e:
            logger.error("u2 dump_hierarchy failed: %s", e)
        return None

    # ── App 管理 ───────────────────────────────────────────────

    def current_activity(self) -> Tuple[str, str]:
        """返回 (package, activity)"""
        try:
            self.ensure_connected()
            info = self.device.app_current()
            pkg = info.get("package", "")
            act = info.get("activity", "")
            return pkg, act
        except Exception:
            return "", ""

    def current_package(self) -> str:
        pkg, _ = self.current_activity()
        return pkg

    def start_app(self, package: str) -> AdbResult:
        try:
            self.device.app_start(package)
            return AdbResult(0, "ok", "", 0)
        except Exception as e:
            return AdbResult(1, "", str(e), 0)

    def force_stop(self, package: str) -> AdbResult:
        try:
            self.device.app_stop(package)
            return AdbResult(0, "ok", "", 0)
        except Exception as e:
            return AdbResult(1, "", str(e), 0)

    def clear_app_data(self, package: str) -> AdbResult:
        return self.shell(f"pm clear {package}")

    def is_app_installed(self, package: str) -> bool:
        try:
            self.ensure_connected()
            return self.device.app_wait(package, timeout=2) is not None
        except Exception:
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
        try:
            self.ensure_connected()
            info = self.device.window_size()
            return info[0], info[1]
        except Exception:
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
