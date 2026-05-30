"""
从拼多多「搜图结果」页点击进入详情，解析 goods_id，生成 H5 商品链接。

uiautomator2 版本：利用 device.app_current() 直接获取当前 Activity 和 Intent 参数，
比 dumpsys 更快更稳定。
"""
from __future__ import annotations

import logging
import re
import time
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .u2_client import U2Client
    from ..pdd_photo.result_parser import CandidateItem

logger = logging.getLogger(__name__)

PDD_GOODS_H5 = "https://mobile.yangkeduo.com/goods.html?goods_id={}"

_GOODS_ID_PATTERNS = [
    re.compile(r"goods_id=(\d{8,22})", re.I),
    re.compile(r"goodsId[=\":\s]+(\d{8,22})", re.I),
    re.compile(r'"goods_id"\s*:\s*"?(\d{8,22})"?'),
    re.compile(r'"goodsId"\s*:\s*"?(\d{8,22})"?', re.I),
    re.compile(r"group_goods_id=(\d{8,22})", re.I),
]


def _parse_goods_id_from_text(text: str) -> Optional[str]:
    if not text:
        return None
    found: list[str] = []
    for pat in _GOODS_ID_PATTERNS:
        found.extend(pat.findall(text))
    if not found:
        return None
    return found[-1]


def extract_goods_id_from_u2(client: "U2Client") -> Optional[str]:
    """从 uiautomator2 获取的当前 Activity 信息中解析 goods_id。

    优先用 device.app_current()（含 intent 参数），
    失败时回退到 adb shell dumpsys。
    """
    try:
        info = client.device.app_current()
        intent = info.get("intent", "") or ""
        data = info.get("data", "") or ""
        combined = f"{intent} {data}"
        gid = _parse_goods_id_from_text(combined)
        if gid:
            return gid
    except Exception:
        pass

    r = client.shell("dumpsys activity top 2>/dev/null", timeout=8)
    return _parse_goods_id_from_text(r.stdout or "")


def fill_product_links_from_detail_taps(
    client: "U2Client",
    candidates: list["CandidateItem"],
    max_items: int = 4,
    tap_wait_s: float = 1.0,
    back_wait_s: float = 0.5,
) -> int:
    """
    依次点击候选卡片的中心进入详情，读取 goods_id，按返回键回到列表。
    成功写入 candidate.pdd_goods_id / candidate.product_url。
    返回成功解析条数。
    """
    ok = 0
    for c in candidates[:max_items]:
        if not c.card_bounds:
            logger.debug("skip link extract pos=%d: no card_bounds", c.position)
            continue
        x1, y1, x2, y2 = c.card_bounds
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        try:
            client.tap(cx, cy)
            time.sleep(tap_wait_s)
            gid = extract_goods_id_from_u2(client)
            if gid:
                c.pdd_goods_id = gid
                c.product_url = PDD_GOODS_H5.format(gid)
                ok += 1
                logger.info("PDD goods_id pos=%d -> %s", c.position, gid)
            else:
                logger.warning("PDD link extract pos=%d: goods_id not found", c.position)
        except Exception as e:
            logger.warning("PDD link extract pos=%d failed: %s", c.position, e)
        finally:
            client.press_back()
            time.sleep(back_wait_s)
    return ok
