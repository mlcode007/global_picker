"""
页面检测器 —— 通过 UI XML + 文字匹配判断当前处于拼多多哪个页面。

支持多层识别策略：
1. uiautomator XML 节点 text / resource-id / content-desc
2. 截图 OCR（作为备用，当前版本先做 XML 层）
3. Activity 名判断
"""
from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Optional

from .adb_client import AdbClient

logger = logging.getLogger(__name__)


class PageType(Enum):
    UNKNOWN = auto()
    LAUNCHER = auto()          # Android 桌面
    PDD_HOME = auto()          # 拼多多首页
    PDD_SEARCH = auto()        # 搜索页
    PDD_CAMERA = auto()        # 相机/拍照页
    PDD_GALLERY = auto()       # 系统相册选择器
    PDD_PHOTO_RESULT = auto()  # 拍照购结果页
    PDD_PRODUCT_DETAIL = auto()  # 商品详情页
    PDD_DIALOG = auto()        # 弹窗覆盖
    PERMISSION_DIALOG = auto() # 系统权限弹窗
    OTHER_APP = auto()


@dataclass
class PageInfo:
    page_type: PageType
    package: str = ""
    activity: str = ""
    xml_path: Optional[str] = None
    matched_texts: list[str] = None

    def __post_init__(self):
        if self.matched_texts is None:
            self.matched_texts = []


PDD_PACKAGE = "com.xunmeng.pinduoduo"

HOME_INDICATORS = ["首页", "推荐", "关注", "百亿补贴", "个人中心", "分类"]
SEARCH_INDICATORS = ["搜索", "热搜", "大家都在搜"]
CAMERA_INDICATORS = ["拍照购", "拍照", "识图", "扫一扫", "相册"]
RESULT_INDICATORS = ["相似商品", "同款", "找相似", "为你推荐", "搜索结果"]
DETAIL_INDICATORS = ["加入购物车", "立即购买", "拼单", "已拼", "商品详情"]
DIALOG_INDICATORS = ["知道了", "我知道了", "取消", "关闭", "以后再说", "暂不", "下次再说", "允许", "稍后提醒", "重试"]
PERMISSION_INDICATORS = ["允许", "始终允许", "仅在使用中允许", "仅此一次"]


class PageDetector:

    def __init__(self, adb: AdbClient):
        self.adb = adb

    def detect(self, tag: str = "") -> PageInfo:
        pkg, act = self.adb.current_activity()

        if pkg and pkg != PDD_PACKAGE:
            if "permission" in act.lower() or "grant" in act.lower():
                return PageInfo(PageType.PERMISSION_DIALOG, pkg, act)
            if "launcher" in pkg.lower() or "home" in pkg.lower():
                return PageInfo(PageType.LAUNCHER, pkg, act)
            if "gallery" in pkg.lower() or "photo" in pkg.lower() or "documentsui" in pkg.lower():
                return PageInfo(PageType.PDD_GALLERY, pkg, act)
            return PageInfo(PageType.OTHER_APP, pkg, act)

        xml_path = self.adb.dump_ui_xml(tag=tag)
        if not xml_path:
            return PageInfo(PageType.UNKNOWN, pkg, act)

        texts = self._extract_texts(xml_path)

        if self._has_permission_dialog(texts):
            return PageInfo(PageType.PERMISSION_DIALOG, pkg, act, xml_path, texts)

        if self._has_dialog(texts):
            return PageInfo(PageType.PDD_DIALOG, pkg, act, xml_path, texts)

        page_type = self._classify_page(texts, act)
        return PageInfo(page_type, pkg, act, xml_path, texts)

    def _extract_texts(self, xml_path: str) -> list[str]:
        texts = []
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            for node in root.iter("node"):
                for attr in ("text", "content-desc"):
                    val = node.get(attr, "").strip()
                    if val:
                        texts.append(val)
        except ET.ParseError:
            logger.warning("Failed to parse XML: %s", xml_path)
        return texts

    def _has_permission_dialog(self, texts: list[str]) -> bool:
        joined = " ".join(texts)
        return any(kw in joined for kw in PERMISSION_INDICATORS) and (
            "访问" in joined or "权限" in joined or "允许" in joined
        )

    def _has_dialog(self, texts: list[str]) -> bool:
        joined = " ".join(texts)
        match_count = sum(1 for kw in DIALOG_INDICATORS if kw in joined)
        return match_count >= 2

    def _classify_page(self, texts: list[str], activity: str) -> PageType:
        joined = " ".join(texts)

        scores = {
            PageType.PDD_PHOTO_RESULT: sum(1 for k in RESULT_INDICATORS if k in joined),
            PageType.PDD_PRODUCT_DETAIL: sum(1 for k in DETAIL_INDICATORS if k in joined),
            PageType.PDD_CAMERA: sum(1 for k in CAMERA_INDICATORS if k in joined),
            PageType.PDD_SEARCH: sum(1 for k in SEARCH_INDICATORS if k in joined),
            PageType.PDD_HOME: sum(1 for k in HOME_INDICATORS if k in joined),
        }

        best = max(scores, key=scores.get)
        if scores[best] >= 2:
            return best

        if scores[best] == 1:
            return best

        return PageType.UNKNOWN

    # ── 节点定位辅助 ──────────────────────────────────────────

    def find_node_by_text(self, xml_path: str, keywords: list[str],
                          max_area: int = 0, prefer_smallest: bool = True) -> Optional[dict]:
        """在 XML 中找到包含关键词的节点，返回其 bounds 中心坐标。
        
        prefer_smallest=True 时优先选面积最小的节点（避免选中大容器），
        max_area>0 时过滤掉面积超过阈值的节点。
        """
        try:
            tree = ET.parse(xml_path)
        except ET.ParseError:
            return None

        candidates = []
        for node in tree.getroot().iter("node"):
            text = node.get("text", "") + " " + node.get("content-desc", "")
            if any(kw in text for kw in keywords):
                bounds = self._parse_bounds(node.get("bounds", ""))
                if bounds:
                    area = (bounds[2] - bounds[0]) * (bounds[3] - bounds[1])
                    if max_area > 0 and area > max_area:
                        continue
                    candidates.append({
                        "text": text.strip(),
                        "bounds": bounds,
                        "center": ((bounds[0] + bounds[2]) // 2, (bounds[1] + bounds[3]) // 2),
                        "resource_id": node.get("resource-id", ""),
                        "clickable": node.get("clickable", "false") == "true",
                        "_area": area,
                    })

        if not candidates:
            return None
        if prefer_smallest:
            candidates.sort(key=lambda c: c["_area"])
        return candidates[0]

    def find_nodes_by_text(self, xml_path: str, keywords: list[str]) -> list[dict]:
        results = []
        try:
            tree = ET.parse(xml_path)
        except ET.ParseError:
            return results

        for node in tree.getroot().iter("node"):
            text = node.get("text", "") + " " + node.get("content-desc", "")
            if any(kw in text for kw in keywords):
                bounds = self._parse_bounds(node.get("bounds", ""))
                if bounds:
                    results.append({
                        "text": text.strip(),
                        "bounds": bounds,
                        "center": ((bounds[0] + bounds[2]) // 2, (bounds[1] + bounds[3]) // 2),
                        "resource_id": node.get("resource-id", ""),
                        "clickable": node.get("clickable", "false") == "true",
                    })
        return results

    def find_node_by_resource_id(self, xml_path: str, res_id: str) -> Optional[dict]:
        try:
            tree = ET.parse(xml_path)
        except ET.ParseError:
            return None

        for node in tree.getroot().iter("node"):
            if res_id in node.get("resource-id", ""):
                bounds = self._parse_bounds(node.get("bounds", ""))
                if bounds:
                    return {
                        "text": node.get("text", ""),
                        "bounds": bounds,
                        "center": ((bounds[0] + bounds[2]) // 2, (bounds[1] + bounds[3]) // 2),
                        "resource_id": node.get("resource-id", ""),
                    }
        return None

    @staticmethod
    def _parse_bounds(bounds_str: str) -> Optional[tuple]:
        m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds_str)
        if m:
            return tuple(int(x) for x in m.groups())
        return None
