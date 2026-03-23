"""
结果解析器 —— 从拍照购结果页的 XML dump 中提取候选商品。

拼多多 XML 结构特点（实测）：
- 价格分两个节点：一个 text="¥"，紧邻下一个 text="7.99"
- 标题节点 resource-id 含 tv_title
- 销量节点如 "本店已拼104万+件" 或 "全店总售172万+件"
- 商品卡片区域按 Y 坐标分组
"""
from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Optional

logger = logging.getLogger(__name__)

PRICE_NUM_PATTERN = re.compile(r"^(\d+(?:\.\d{1,2})?)$")
PRICE_INLINE_PATTERN = re.compile(r"[¥￥]\s*(\d+(?:\.\d{1,2})?)")
SALES_PATTERN = re.compile(r"(?:已拼|已售|总售|销量|月销)\s*(\d[\d.]*万?)\+?件?")
TITLE_RID_KEYWORDS = ["tv_title", "title", "goods_name"]
SKIP_TEXTS = {"推荐", "百货", "鞋包", "食品", "饰品", "手机", "家纺", "男装",
              "首页", "直播", "上新优惠", "聊天", "个人中心", "拍照搜索",
              "百亿补贴", "多多买菜", "明天自提", "限时秒杀", "补贴多人团",
              "现金大转盘", "多多果园", "其他"}


@dataclass
class CandidateItem:
    title: str = ""
    price: Optional[Decimal] = None
    original_price: Optional[Decimal] = None
    sales_text: str = ""
    sales_volume: Optional[int] = None
    shop_name: str = ""
    image_url: str = ""
    position: int = 0
    bounds_y: int = 0
    # 商品主图在截图中的裁剪坐标 (x1, y1, x2, y2)
    image_bounds: Optional[tuple] = None

    @property
    def is_valid(self) -> bool:
        return bool(self.title) and self.price is not None and self.price > 0


@dataclass
class ParseResult:
    candidates: list[CandidateItem] = field(default_factory=list)
    raw_texts: list[str] = field(default_factory=list)
    parse_errors: list[str] = field(default_factory=list)


@dataclass
class _NodeInfo:
    index: int
    text: str
    content_desc: str
    resource_id: str
    bounds: Optional[tuple] = None
    center_y: int = 0


class ResultParser:

    def parse_xml_files(self, xml_paths: list[str]) -> ParseResult:
        result = ParseResult()
        all_candidates = []

        for path in xml_paths:
            items = self._parse_single_xml(path, result)
            all_candidates.extend(items)

        result.candidates = self._deduplicate(all_candidates)

        for i, c in enumerate(result.candidates):
            c.position = i + 1

        logger.info("Parsed %d unique candidates from %d XML files",
                     len(result.candidates), len(xml_paths))
        return result

    def _parse_single_xml(self, xml_path: str, result: ParseResult) -> list[CandidateItem]:
        try:
            tree = ET.parse(xml_path)
        except ET.ParseError as e:
            result.parse_errors.append(f"XML parse error: {xml_path}: {e}")
            return []

        root = tree.getroot()
        raw_nodes = list(root.iter("node"))

        nodes: list[_NodeInfo] = []
        # 收集所有大尺寸 ImageView 的 bounds，用于后续匹配商品主图
        product_image_bounds: list[tuple] = []
        for i, n in enumerate(raw_nodes):
            text = n.get("text", "").strip()
            cd = n.get("content-desc", "").strip()
            rid = n.get("resource-id", "")
            bounds = self._parse_bounds(n.get("bounds", ""))
            cy = (bounds[1] + bounds[3]) // 2 if bounds else 0
            if text or cd:
                nodes.append(_NodeInfo(i, text, cd, rid, bounds, cy))
                result.raw_texts.append(text or cd)
            # 收集大尺寸 ImageView（宽高均 > 100px）作为商品主图候选
            if (n.get("class", "") == "android.widget.ImageView"
                    and bounds
                    and (bounds[2] - bounds[0]) > 100
                    and (bounds[3] - bounds[1]) > 100):
                product_image_bounds.append(bounds)

        candidates = self._extract_product_cards(nodes)
        self._assign_image_bounds(candidates, product_image_bounds)
        return candidates

    def _assign_image_bounds(
        self,
        candidates: list[CandidateItem],
        image_bounds_list: list[tuple],
    ) -> None:
        """将 ImageView bounds 分配给对应候选商品。

        策略：商品图片通常位于标题/价格节点的上方，且 X 坐标范围重叠。
        优先选择 X 范围重叠、且在价格节点上方（或略下方）的最近图片。
        """
        used = set()
        for item in candidates:
            best_idx = None
            best_score = float("inf")
            for i, b in enumerate(image_bounds_list):
                if i in used:
                    continue
                img_cy = (b[1] + b[3]) // 2
                img_cx = (b[0] + b[2]) // 2

                # 图片应在价格节点上方（img_cy < bounds_y）或同行
                # 给上方图片更低的惩罚分
                y_diff = item.bounds_y - img_cy  # 正值=图片在上方
                if y_diff < -200:
                    # 图片在价格节点下方超过 200px，跳过
                    continue

                dist = abs(img_cy - item.bounds_y)
                # 上方图片优先（减少惩罚）
                score = dist - (100 if y_diff > 0 else 0)
                if score < best_score:
                    best_score = score
                    best_idx = i
            if best_idx is not None and best_score < 600:
                item.image_bounds = image_bounds_list[best_idx]
                used.add(best_idx)

    def _extract_product_cards(self, nodes: list[_NodeInfo]) -> list[CandidateItem]:
        """
        策略：找 ¥ 符号节点 + 紧邻价格数字节点 → 定位一个商品卡片，
        然后在附近节点中搜标题、销量、店铺。
        """
        candidates = []
        used = set()

        for idx, node in enumerate(nodes):
            if idx in used:
                continue

            price = self._try_extract_price(nodes, idx)
            if price is None:
                continue

            if price <= 0 or price > 99999:
                continue

            item = CandidateItem(
                price=price,
                bounds_y=node.center_y,
            )
            used.add(idx)

            price_num_idx = self._find_price_number_idx(nodes, idx)
            if price_num_idx is not None:
                used.add(price_num_idx)

            ref_y = node.center_y
            nearby = self._get_nearby_nodes(nodes, ref_y, radius=200, exclude=used)

            for n in nearby:
                if not item.title and self._looks_like_title(n):
                    item.title = n.text or n.content_desc
                    used.add(nodes.index(n) if n in nodes else -1)

            for n in nearby:
                sm = SALES_PATTERN.search(n.text)
                if sm and not item.sales_text:
                    item.sales_text = n.text
                    item.sales_volume = self._parse_sales(sm.group(1))
                    used.add(nodes.index(n) if n in nodes else -1)

            for n in nearby:
                if not item.shop_name and self._looks_like_shop(n.text):
                    item.shop_name = n.text
                    used.add(nodes.index(n) if n in nodes else -1)

            if item.is_valid:
                candidates.append(item)

        return candidates

    def _try_extract_price(self, nodes: list[_NodeInfo], idx: int) -> Optional[Decimal]:
        node = nodes[idx]
        text = node.text

        inline = PRICE_INLINE_PATTERN.search(text)
        if inline:
            try:
                return Decimal(inline.group(1))
            except (InvalidOperation, ValueError):
                pass

        if text in ("¥", "￥", "券后"):
            num_idx = self._find_price_number_idx(nodes, idx)
            if num_idx is not None:
                m = PRICE_NUM_PATTERN.match(nodes[num_idx].text)
                if m:
                    try:
                        return Decimal(m.group(1))
                    except (InvalidOperation, ValueError):
                        pass
        return None

    def _find_price_number_idx(self, nodes: list[_NodeInfo], yen_idx: int) -> Optional[int]:
        for offset in (1, 2):
            j = yen_idx + offset
            if j < len(nodes):
                if PRICE_NUM_PATTERN.match(nodes[j].text):
                    if abs(nodes[j].center_y - nodes[yen_idx].center_y) < 80:
                        return j
        return None

    def _get_nearby_nodes(self, nodes: list[_NodeInfo], ref_y: int, radius: int, exclude: set) -> list[_NodeInfo]:
        result = []
        for i, n in enumerate(nodes):
            if i in exclude:
                continue
            if abs(n.center_y - ref_y) <= radius:
                result.append(n)
        return result

    def _looks_like_title(self, node: _NodeInfo) -> bool:
        text = node.text or node.content_desc
        if len(text) < 4:
            return False
        if text in SKIP_TEXTS:
            return False
        if PRICE_INLINE_PATTERN.search(text):
            return False
        if PRICE_NUM_PATTERN.match(text):
            return False
        if SALES_PATTERN.search(text):
            return False
        if text.startswith("预计") or text.endswith("好评"):
            return False
        if text in ("先用后付",):
            return False
        for kw in TITLE_RID_KEYWORDS:
            if kw in node.resource_id:
                return True
        if len(text) >= 6:
            return True
        return False

    @staticmethod
    def _looks_like_shop(text: str) -> bool:
        if not text or len(text) < 2 or len(text) > 30:
            return False
        shop_kws = ("旗舰店", "专营店", "自营", "官方", "店铺")
        return any(k in text for k in shop_kws)

    def _deduplicate(self, items: list[CandidateItem]) -> list[CandidateItem]:
        seen = set()
        unique = []
        for item in items:
            key = (item.title[:30] if item.title else "", str(item.price))
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)
        return unique

    @staticmethod
    def _parse_sales(text: str) -> Optional[int]:
        text = text.replace("+", "").replace("件", "").strip()
        if "万" in text:
            try:
                return int(float(text.replace("万", "")) * 10000)
            except ValueError:
                return None
        try:
            return int(text)
        except ValueError:
            return None

    @staticmethod
    def _parse_bounds(bounds_str: str) -> Optional[tuple]:
        m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds_str)
        if m:
            return tuple(int(x) for x in m.groups())
        return None
