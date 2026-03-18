"""
工件管理器 —— 保存截图、XML、日志等证据文件。

所有运行时产物统一管理，按 task_id 分目录存放，
方便回溯问题和持久化保存。
"""
from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

BASE_ARTIFACTS_DIR = Path("/Users/smzdm/global_picker/artifacts/pdd_photo")


class ArtifactManager:

    def __init__(self, task_id: int):
        self.task_id = task_id
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.task_dir = BASE_ARTIFACTS_DIR / f"task_{task_id}_{ts}"
        self.task_dir.mkdir(parents=True, exist_ok=True)

    @property
    def screenshots_dir(self) -> Path:
        d = self.task_dir / "screenshots"
        d.mkdir(exist_ok=True)
        return d

    @property
    def xml_dir(self) -> Path:
        d = self.task_dir / "xml"
        d.mkdir(exist_ok=True)
        return d

    @property
    def results_dir(self) -> Path:
        d = self.task_dir / "results"
        d.mkdir(exist_ok=True)
        return d

    def save_screenshot(self, src_path: str, label: str = "") -> Optional[str]:
        if not src_path or not Path(src_path).exists():
            return None
        name = f"{label}_{Path(src_path).name}" if label else Path(src_path).name
        dest = str(self.screenshots_dir / name)
        shutil.copy2(src_path, dest)
        return dest

    def save_xml(self, src_path: str, label: str = "") -> Optional[str]:
        if not src_path or not Path(src_path).exists():
            return None
        name = f"{label}_{Path(src_path).name}" if label else Path(src_path).name
        dest = str(self.xml_dir / name)
        shutil.copy2(src_path, dest)
        return dest

    def save_result_json(self, data: dict, label: str = "result") -> str:
        dest = str(self.results_dir / f"{label}.json")
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        return dest

    def save_step_logs(self, logs: list) -> str:
        serializable = []
        for log in logs:
            if hasattr(log, "__dict__"):
                serializable.append(log.__dict__)
            else:
                serializable.append(str(log))
        return self.save_result_json({"step_logs": serializable}, label="step_logs")

    def get_task_dir(self) -> str:
        return str(self.task_dir)
