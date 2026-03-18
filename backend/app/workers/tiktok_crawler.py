"""
TikTok Shop 商品采集 Worker — Playwright + 代理 + Cookie 版

绕过反爬的两个关键配置（在 .env 中设置）：
  TIKTOK_PROXY   — 住宅代理，格式 http://user:pass@host:port
  TIKTOK_COOKIES — 浏览器登录后的 Cookie JSON

三层采集策略（按优先级依次尝试）：
  Layer 1 — 网络拦截：监听 TikTok 内部 API 响应，拿到结构化 JSON
  Layer 2 — window 全局变量：读取 __NEXT_DATA__ / __INITIAL_STATE__ 等
  Layer 3 — DOM 选择器：从渲染后的页面元素中提取文本
"""
import asyncio
import json
import logging
import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from app.config import get_settings
from app.database import SessionLocal
from app.models.crawl_task import CrawlTask
from app.models.product import Product

logger = logging.getLogger(__name__)

_UA_DESKTOP = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
_UA_MOBILE = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
)

_API_KEYWORDS = [
    "api/v1/product", "api/v2/product",
    "pdp/item_data", "item/detail", "product/detail",
    "item_data", "product_info",
]

_SELECTORS = {
    "title": [
        "[data-testid='pdp-product-title']",
        "h1.product-title",
        ".pdp-mod-product-badge-title",
        "h1[class*='title']",
        "span[class*='ProductTitle']",
        "h1[class*='product']",
        "[class*='ProductTitle']",
        "[class*='product-title']",
        "[class*='itemTitle']",
    ],
    "price": [
        # data-testid 系（优先）
        "[data-testid='pdp-product-price']",
        "[data-testid='pdp-product-price'] span",
        "[data-testid*='sale-price']",
        # TikTok Shop 售价容器（带 icon 的价格块，含 withIcon）
        "[class*='price-withIcon'] span",
        "[class*='withIcon'][class*='price'] span",
        # 常见 sale price 命名
        "[class*='price-sale']",
        "[class*='sale-price']",
        "[class*='salePrice']",
        "[class*='ProductPrice']",
        "[class*='discountPrice']",
        "[class*='DiscountPrice']",
        "[class*='product-price']",
        ".product-price-value",
        # 注意：故意不加 span[class*='price']，会误命中 original-price
    ],
    "sales": [
        "[data-testid='pdp-sold-count']",
        "[data-testid*='sold']",
        "span[class*='sold']",
        "[class*='sales-count']",
        "[class*='soldCount']",
        "[class*='SoldCount']",
        "[class*='sell-count']",
    ],
    "rating": [
        "[data-testid='pdp-review-score']",
        ".pdp-review-summary-star-score",
        "[class*='star-score']",
        "[class*='StarScore']",
        "[class*='review-score']",
        "[class*='ratingScore']",
    ],
    "shop_name": [
        "[data-testid='pdp-shop-name']",
        ".pdp-shop-name",
        "[class*='shop-name'] span",
        "[class*='ShopName']",
        "[class*='shopName']",
        "a[class*='shop'] span",
    ],
    "review_count": [
        "[data-testid='pdp-review-count']",
        "[class*='review-count']",
        "[class*='reviewCount']",
        "[class*='rating-count']",
        "[class*='ratingCount']",
    ],
}

# 浏览器/系统错误页标题关键词（命中则直接拒绝数据）
_ERROR_TITLE_KEYWORDS = [
    "无法访问", "err_", "not found", "error", "404", "403",
    "access denied", "blocked", "403 forbidden", "502", "503",
    "该页面无法正常运作", "页面不可访问",
]

_WINDOW_JS = """
() => {
  const keys = ['__NEXT_DATA__','__INITIAL_STATE__','__SSR_DATA__','__APP_DATA__','__DATA__'];
  for (const k of keys) {
    if (window[k] != null) return window[k];
  }
  return null;
}
"""

_REMIX_JS = r"""
() => {
  try {
    const ctx = window.__remixContext || window.__staticRouterHydrationData;
    if (ctx) {
      const ld = ctx.state?.loaderData || ctx.loaderData;
      if (ld) return ld;
    }
  } catch {}
  try {
    const scripts = document.querySelectorAll('script');
    for (const s of scripts) {
      const t = s.textContent || '';
      if (t.includes('loaderData') && t.includes('productInfo')) {
        const m = t.match(/window\.__remixContext\s*=\s*({.+?});?\s*$/ms)
               || t.match(/({\s*"loaderData".+})/s);
        if (m) return JSON.parse(m[1]).loaderData || JSON.parse(m[1]);
      }
    }
  } catch {}
  return null;
}
"""


# ──────────────────────────────────────────────
# URL 工具
# ──────────────────────────────────────────────

def extract_product_id(url: str) -> Optional[str]:
    m = re.search(r"/product/(\d+)", url)
    return m.group(1) if m else None


def extract_region(url: str) -> str:
    m = re.search(r"[?&]region=([A-Z]{2,3})", url)
    return m.group(1) if m else "PH"


# ──────────────────────────────────────────────
# 数据工具
# ──────────────────────────────────────────────

def _safe_decimal(val) -> Optional[Decimal]:
    try:
        if val is None:
            return None
        s = re.sub(r"[^\d.]", "", str(val)).strip(".")
        return Decimal(s) if s else None
    except (InvalidOperation, ValueError):
        return None


def _safe_int(val) -> Optional[int]:
    try:
        if val is None:
            return None
        s = re.sub(r"[^\d]", "", str(val))
        return int(s) if s else None
    except (ValueError, TypeError):
        return None


def _dig(data, *keys):
    for key in keys:
        if not isinstance(data, dict):
            return None
        data = data.get(key)
    return data


# ──────────────────────────────────────────────
# Cookie 加载
# ──────────────────────────────────────────────

def _load_cookies() -> list[dict]:
    """
    从 TIKTOK_COOKIES 配置读取 cookie。
    支持两种格式：
      1. JSON 对象: {"sessionid": "xxx", "msToken": "yyy"}
      2. Netscape 格式字符串: name=value; name2=value2
    返回 Playwright context.add_cookies() 所需格式。
    """
    raw = get_settings().TIKTOK_COOKIES.strip()
    if not raw:
        return []

    cookies = []
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            for name, value in data.items():
                cookies.append({
                    "name": name, "value": str(value),
                    "domain": ".tiktok.com", "path": "/",
                })
        elif isinstance(data, list):
            cookies = data
    except json.JSONDecodeError:
        # name=value; name2=value2 格式
        for pair in raw.split(";"):
            pair = pair.strip()
            if "=" in pair:
                name, _, value = pair.partition("=")
                cookies.append({
                    "name": name.strip(), "value": value.strip(),
                    "domain": ".tiktok.com", "path": "/",
                })
    return cookies


# ──────────────────────────────────────────────
# Layer 1：API 响应拦截
# ──────────────────────────────────────────────

def _is_product_api(url: str) -> bool:
    return any(kw in url for kw in _API_KEYWORDS)


def _extract_from_api_json(data: dict) -> dict:
    candidates = [
        _dig(data, "data", "product"),
        _dig(data, "data", "item"),
        _dig(data, "result", "product"),
        _dig(data, "data"),
        data,
    ]
    for c in candidates:
        if c and isinstance(c, dict) and (
            c.get("title") or c.get("name") or c.get("itemTitle")
        ):
            return c
    return {}


# ──────────────────────────────────────────────
# Layer 2：window 全局变量
# ──────────────────────────────────────────────

def _parse_window_data(raw: dict) -> dict:
    if not raw:
        return {}
    candidates = [
        _dig(raw, "props", "pageProps", "product"),
        _dig(raw, "props", "pageProps", "itemData"),
        _dig(raw, "props", "pageProps", "data", "product"),
        _dig(raw, "props", "pageProps", "data"),
        _dig(raw, "initialState", "productDetail", "product"),
        _dig(raw, "product"), _dig(raw, "item"),
    ]
    for c in candidates:
        if c and isinstance(c, dict) and (
            c.get("title") or c.get("name") or c.get("itemTitle")
        ):
            return c
    return {}


def _parse_remix_loader_data(raw: dict) -> dict:
    """从 Remix loaderData 中提取 TikTok Shop productInfo 并转为统一格式。"""
    if not raw or not isinstance(raw, dict):
        return {}

    product_info = None
    real_region = None
    for key, val in raw.items():
        if not isinstance(val, dict):
            continue
        pi = _dig(val, "initialData", "productInfo")
        if pi and isinstance(pi, dict) and pi.get("product_id"):
            product_info = pi
            real_region = val.get("realRegion")
            break

    if not product_info:
        return {}

    pb = product_info.get("product_base") or {}
    seller = product_info.get("seller") or {}
    review = product_info.get("product_detail_review") or {}
    shipping_data = product_info.get("shipping") or {}
    logistics_list = shipping_data.get("logistics") or []
    logistics = logistics_list[0] if logistics_list else {}
    skus = product_info.get("skus") or []

    images_raw = pb.get("images") or []
    image_urls = []
    for img in images_raw[:10]:
        urls = img.get("url_list") or []
        if urls:
            image_urls.append(urls[0])

    price_val = None
    currency = None
    original_price_val = None
    discount_text = None
    if skus:
        sku_price = skus[0].get("price") or {}
        rp = sku_price.get("real_price") or {}
        price_val = rp.get("price_val")
        currency = rp.get("currency")
        original_price_val = sku_price.get("original_price_value")
        discount_text = sku_price.get("discount")

    ship_fee_obj = logistics.get("shipping_fee") or {}

    result = {
        "title": pb.get("title"),
        "images": image_urls,
        "soldCount": pb.get("sold_count"),
        "price": price_val,
        "currency": currency,
        "originalPrice": original_price_val,
        "discount": discount_text,
        "rating": review.get("product_rating"),
        "reviewCount": review.get("review_count"),
        "shop": {
            "name": seller.get("name"),
            "id": str(seller.get("seller_id", "")),
        },
        "sellerLocation": seller.get("seller_location"),
        "shippingFee": ship_fee_obj.get("price_val"),
        "shippingCurrency": ship_fee_obj.get("currency"),
        "freeShipping": logistics.get("free_shipping"),
        "deliveryDaysMin": logistics.get("delivery_min_days"),
        "deliveryDaysMax": logistics.get("delivery_max_days"),
        "region": real_region,
        "_source": "remix_loader_data",
    }
    return {k: v for k, v in result.items() if v is not None}


# ──────────────────────────────────────────────
# Layer 3：DOM 选择器
# ──────────────────────────────────────────────

async def _scrape_dom(page) -> dict:
    result = {}

    async def first_text(selectors: list, field: str = "") -> Optional[str]:
        for sel in selectors:
            try:
                el = await page.query_selector(sel)
                if el:
                    t = (await el.inner_text()).strip()
                    if t:
                        logger.debug("DOM[%s] 命中 selector=%s  value=%r", field, sel, t[:80])
                        return t
            except Exception:
                continue
        logger.debug("DOM[%s] 所有选择器未命中", field)
        return None

    if title := await first_text(_SELECTORS["title"], "title"):
        result["title"] = title
    if price := await first_text(_SELECTORS["price"], "price"):
        result["price"] = price
    if sales := await first_text(_SELECTORS["sales"], "sales"):
        result["salesVolume"] = re.sub(r"[^\d]", "", sales)
    if rating := await first_text(_SELECTORS["rating"], "rating"):
        result["rating"] = rating
    if shop := await first_text(_SELECTORS["shop_name"], "shop_name"):
        result["shop"] = {"name": shop}
    if review := await first_text(_SELECTORS["review_count"], "review_count"):
        result["reviewCount"] = re.sub(r"[^\d]", "", review)

    # JS 兜底：扫描价格相关元素，跳过原价/划线价容器
    if "price" not in result:
        try:
            price_js = await page.evaluate("""() => {
                const currency = ['PHP','USD','MYR','SGD','THB','VND','IDR','₱','$','RM','฿'];
                // 排除关键词：original / discount / crossed / del / strike
                const excludeKw = ['original', 'discount', 'crossed', 'del', 'strike', 'through'];
                // 优先找带 withIcon / salePrice / price 类名的元素
                const candidates = document.querySelectorAll(
                    '[class*="withIcon"], [class*="salePrice"], [class*="sale-price"], [class*="price-sale"]'
                );
                for (const el of candidates) {
                    const cls = (el.className || '').toLowerCase();
                    if (excludeKw.some(k => cls.includes(k))) continue;
                    const t = el.innerText?.trim();
                    if (t && t.length < 30 && currency.some(c => t.includes(c)) && /[\\d]/.test(t)) {
                        return t;
                    }
                }
                // 再次兜底：遍历所有文本节点，但跳过含 original/discount 祖先元素
                const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                let node;
                while ((node = walker.nextNode())) {
                    const t = node.textContent.trim();
                    if (t.length < 20 && currency.some(c => t.includes(c)) && /[\\d]/.test(t)) {
                        let el = node.parentElement;
                        let skip = false;
                        while (el) {
                            const cls = (el.className || '').toLowerCase();
                            if (excludeKw.some(k => cls.includes(k))) { skip = true; break; }
                            el = el.parentElement;
                        }
                        if (!skip) return t;
                    }
                }
                return null;
            }""")
            if price_js:
                logger.debug("DOM[price] JS兜底命中: %r", price_js)
                result["price"] = price_js
        except Exception as e:
            logger.debug("DOM[price] JS兜底异常: %s", e)

    _IMG_CDN_DOMAINS = ("ibyteimg.com", "tiktokcdn.com", "tiktok.com", "tiktokcdn-us.com")

    try:
        imgs = await page.query_selector_all(
            "img[class*='product'], img[class*='main'], "
            ".swiper-slide img, .slick-slide img, "
            "[class*='gallery'] img, [class*='item-'] img, "
            "[class*='carousel'] img, [class*='slider'] img"
        )
        urls = []
        for img in imgs[:10]:
            src = await img.get_attribute("src")
            if src and src.startswith("http") and any(d in src for d in _IMG_CDN_DOMAINS):
                urls.append(src)
        if urls:
            result["images"] = urls
    except Exception:
        pass

    if "images" not in result:
        try:
            js_imgs = await page.evaluate("""() => {
                const cdns = ['ibyteimg.com', 'tiktokcdn.com', 'tiktok.com', 'tiktokcdn-us.com'];
                const imgs = document.querySelectorAll(
                    '.slick-slide img, .swiper-slide img, [class*="item-"] img, [data-fmp] img'
                );
                const urls = [];
                for (const img of imgs) {
                    const src = img.src || img.getAttribute('src');
                    if (src && src.startsWith('http') && cdns.some(d => src.includes(d))) {
                        if (!urls.includes(src)) urls.push(src);
                    }
                    if (urls.length >= 10) break;
                }
                return urls;
            }""")
            if js_imgs:
                result["images"] = js_imgs
        except Exception:
            pass

    return result


# ──────────────────────────────────────────────
# 写入 Product 模型
# ──────────────────────────────────────────────

def _apply_product_data(product: Product, data: dict, db: "Session | None" = None) -> bool:
    updated = False

    title = (
        data.get("title") or data.get("name")
        or data.get("itemTitle") or data.get("productName")
    )
    if title:
        new_title = str(title)[:512]
        if new_title != product.title:
            product.title = new_title
            updated = True

    price_raw = (
        _dig(data, "price", "salePrice")
        or _dig(data, "priceInfo", "minPrice")
        or _dig(data, "priceInfo", "price")
        or data.get("salePrice") or data.get("price")
    )
    if price_raw:
        d = _safe_decimal(price_raw)
        if d is not None:
            new_price = d / 100 if d > 10000 else d
            if new_price != product.price:
                product.price = new_price
                updated = True

    for key in ("salesVolume", "sold", "sales", "soldCount"):
        n = _safe_int(data.get(key))
        if n is not None:
            product.sales_volume = n
            updated = True
            break

    rating_raw = data.get("rating") or data.get("score") or _dig(data, "ratingInfo", "score")
    if r := _safe_decimal(rating_raw):
        product.rating = r
        updated = True

    review_raw = (
        data.get("reviewCount") or data.get("commentCount")
        or _dig(data, "ratingInfo", "ratingCount")
    )
    if rc := _safe_int(review_raw):
        product.review_count = rc
        updated = True

    shop = data.get("shop") or data.get("seller") or data.get("shopInfo") or {}
    shop_name = (
        shop.get("name") or shop.get("shopName") or shop.get("title")
        if isinstance(shop, dict) else str(shop) if shop else None
    )
    shop_id = shop.get("id") or shop.get("shopId") if isinstance(shop, dict) else None
    if shop_name and not product.shop_name:
        product.shop_name = str(shop_name)[:256]
        updated = True
    if shop_id and not product.shop_id:
        product.shop_id = str(shop_id)[:64]
        updated = True

    images = data.get("images") or data.get("imageList") or data.get("imgs") or []
    if images and not product.main_image_url:
        def _img_url(img):
            if isinstance(img, dict):
                return img.get("url") or img.get("thumb") or (img.get("urlList") or [None])[0]
            return str(img)
        urls = [u for u in (_img_url(i) for i in images[:10]) if u]
        if urls:
            product.main_image_url = urls[0]
            product.image_urls = urls
            updated = True

    category = (
        data.get("category") or data.get("categoryName")
        or _dig(data, "categoryInfo", "name")
    )
    if category and not product.category:
        product.category = str(category)[:128]
        updated = True

    if cur := data.get("currency"):
        if cur != product.currency:
            product.currency = str(cur)[:8]
            updated = True

    if rgn := data.get("region"):
        if rgn != product.region:
            product.region = str(rgn)[:16]
            updated = True

    # 若币种仍是默认值且有 region，尝试根据 region 推断正确币种
    from app.services.exchange_rate_service import currency_for_region
    if product.region and (not data.get("currency")):
        inferred = currency_for_region(product.region)
        if inferred and inferred != product.currency:
            product.currency = inferred
            updated = True

    if op := _safe_decimal(data.get("originalPrice")):
        product.original_price = op / 100 if op > 10000 else op
        updated = True

    if disc := data.get("discount"):
        product.discount = str(disc)[:16]
        updated = True

    if loc := data.get("sellerLocation"):
        product.seller_location = str(loc)[:64]
        updated = True

    if sf := _safe_decimal(data.get("shippingFee")):
        product.shipping_fee = sf
        updated = True

    if data.get("freeShipping") is not None:
        product.free_shipping = 1 if data["freeShipping"] else 0
        updated = True

    if (d_min := _safe_int(data.get("deliveryDaysMin"))) is not None:
        product.delivery_days_min = d_min
        updated = True

    if (d_max := _safe_int(data.get("deliveryDaysMax"))) is not None:
        product.delivery_days_max = d_max
        updated = True

    # 自动换算 price_cny
    if db and product.price and product.currency:
        from app.services.exchange_rate_service import convert_to_cny
        cny = convert_to_cny(db, product.price, product.currency)
        if cny is not None and cny != product.price_cny:
            product.price_cny = cny
            updated = True

    return updated


# ──────────────────────────────────────────────
# Playwright 核心采集
# ──────────────────────────────────────────────

async def _fetch_with_playwright(url: str) -> dict:
    from playwright.async_api import async_playwright, TimeoutError as PwTimeout
    from playwright_stealth import Stealth

    settings = get_settings()
    proxy_cfg = {"server": settings.TIKTOK_PROXY} if settings.TIKTOK_PROXY.strip() else None
    cookies = _load_cookies()

    product_data: dict = {}
    intercepted: list[dict] = []

    async with async_playwright() as pw:
        headless = settings.TIKTOK_HEADLESS
        launch_opts = {
            "headless": headless,
            "slow_mo": 0 if headless else 200,   # 有头模式适当减速，更像人类操作
            "args": [
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ],
        }
        if proxy_cfg:
            launch_opts["proxy"] = proxy_cfg

        browser = await pw.chromium.launch(**launch_opts)

        context_opts = {
            "user_agent": _UA_DESKTOP,
            "locale": "en-PH",
            "timezone_id": "Asia/Manila",
            "viewport": {"width": 1280, "height": 900},
            "extra_http_headers": {
                "Accept-Language": "en-US,en;q=0.9",
                "sec-fetch-dest": "document",
                "sec-fetch-mode": "navigate",
            },
        }
        context = await browser.new_context(**context_opts)

        # 注入 Cookie（绕过 CAPTCHA 的关键）
        if cookies:
            await context.add_cookies(cookies)
            logger.info("已注入 %d 条 TikTok Cookie", len(cookies))

        page = await context.new_page()
        await Stealth().apply_stealth_async(page)

        # Layer 1 拦截
        async def on_response(resp):
            if _is_product_api(resp.url):
                try:
                    body = await resp.json()
                    intercepted.append(body)
                except Exception:
                    pass

        page.on("response", on_response)

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            await page.wait_for_load_state("networkidle", timeout=20_000)
        except PwTimeout:
            logger.warning("页面加载超时，等待 10s 后继续解析已有内容")
            await asyncio.sleep(10)
        except Exception as e:
            logger.warning("页面加载异常: %s，等待 10s 后继续尝试解析", e)
            await asyncio.sleep(10)

        # ── 检查是否为浏览器/网络错误页 ──────────────────────────────
        final_url = page.url
        page_title = await page.title()
        page_title_lower = page_title.lower()

        if final_url.startswith("chrome-error://") or not final_url.startswith("http"):
            await browser.close()
            raise RuntimeError(
                f"页面无法访问（URL：{final_url}），请检查网络连接或 URL 是否有效。"
            )

        for kw in _ERROR_TITLE_KEYWORDS:
            if kw in page_title_lower:
                await browser.close()
                raise RuntimeError(
                    f"页面显示错误（标题：{page_title}），可能是网络不通、IP 被封或 URL 无效。"
                )

        # ── 检查是否触发 CAPTCHA ──────────────────────────────────────
        is_captcha = "security" in page_title_lower or "captcha" in page_title_lower

        if is_captcha:
            if not headless:
                # 有头模式：等待用户在弹出的浏览器窗口中手动过验证（最多 120 秒）
                logger.warning(
                    "crawl task %s 触发 CAPTCHA，等待用户在浏览器窗口中手动通过（120s 超时）",
                    url
                )
                try:
                    # 等待页面标题变为非 CAPTCHA（说明验证通过，页面跳转）
                    await page.wait_for_function(
                        """() => {
                            const t = document.title.toLowerCase();
                            return !t.includes('security') && !t.includes('captcha') && t.length > 0;
                        }""",
                        timeout=120_000,
                    )
                    # 验证通过后重新等待页面稳定
                    await page.wait_for_load_state("networkidle", timeout=20_000)
                    logger.info("CAPTCHA 已手动通过，继续采集")
                except PwTimeout:
                    await browser.close()
                    raise RuntimeError("等待手动过验证超时（120s），请刷新后重试")
            else:
                # 无头模式：无法手动操作，直接报错
                await browser.close()
                raise RuntimeError(
                    "触发 CAPTCHA 安全验证（无头模式）。解决方案：\n"
                    "① 设置 TIKTOK_HEADLESS=False 后手动在弹出窗口中通过验证\n"
                    "② 在 .env 设置 TIKTOK_PROXY（住宅代理）\n"
                    "③ 在 .env 设置 TIKTOK_COOKIES（从浏览器复制登录 Cookie）"
                )

        # Layer 0 — Remix loaderData（TikTok Shop 当前架构，最可靠）
        try:
            remix_data = await page.evaluate(_REMIX_JS)
            data = _parse_remix_loader_data(remix_data or {})
            if data and data.get("title"):
                logger.info("Layer0 命中：Remix loaderData (fields=%d)", len(data))
                product_data = data
        except Exception as e:
            logger.debug("Layer0 失败: %s", e)

        # Layer 1
        if not product_data:
            for resp_body in intercepted:
                data = _extract_from_api_json(resp_body)
                if data:
                    logger.info("Layer1 命中：API 响应拦截")
                    product_data = data
                    break

        # Layer 2
        if not product_data:
            try:
                win_data = await page.evaluate(_WINDOW_JS)
                data = _parse_window_data(win_data or {})
                if data:
                    logger.info("Layer2 命中：window 全局变量")
                    product_data = data
            except Exception as e:
                logger.debug("Layer2 失败: %s", e)

        # Layer 3
        if not product_data:
            try:
                data = await _scrape_dom(page)
                if data.get("title") or data.get("price"):
                    logger.info("Layer3 命中：DOM 选择器")
                    product_data = data
            except Exception as e:
                logger.debug("Layer3 失败: %s", e)

        await browser.close()

    # ── 数据合法性校验：防止将错误页内容写入数据库 ──────────────────
    if product_data:
        raw_title = (product_data.get("title") or "").lower()
        for kw in _ERROR_TITLE_KEYWORDS:
            if kw in raw_title:
                logger.warning("采集到的标题疑似错误页内容（%s），丢弃数据", product_data.get("title"))
                return None

    return product_data


# ──────────────────────────────────────────────
# 后台任务主入口
# ──────────────────────────────────────────────

async def run_crawl_task(task_id: int) -> None:
    db = SessionLocal()
    try:
        task: Optional[CrawlTask] = (
            db.query(CrawlTask).filter(CrawlTask.id == task_id).first()
        )
        if not task or task.status not in ("pending", "failed"):
            return

        task.status = "running"
        db.commit()

        product: Optional[Product] = (
            db.query(Product).filter(Product.crawl_task_id == task_id).first()
        )
        if not product:
            task.status = "failed"
            task.error_msg = "关联商品记录不存在"
            db.commit()
            return

        product_id = extract_product_id(task.url)
        region = extract_region(task.url)

        if not product_id:
            task.status = "failed"
            task.error_msg = "无法从链接中提取商品ID，请确认链接格式"
            db.commit()
            return

        product.tiktok_product_id = product_id
        product.region = region

        try:
            data = await _fetch_with_playwright(task.url)

            if data:
                _apply_product_data(product, data, db=db)
                task.status = "done"
                task.error_msg = None
                logger.info("crawl task %d done (product_id=%s)", task_id, product_id)
            else:
                task.status = "failed"
                task.error_msg = "三层策略均未采集到数据"
                task.retry_count += 1

        except RuntimeError as e:
            # CAPTCHA 提示，给用户看得懂的错误
            task.status = "failed"
            task.error_msg = str(e)
            task.retry_count += 1
        except Exception as e:
            task.status = "failed"
            task.error_msg = str(e)[:500]
            task.retry_count += 1
            logger.exception("crawl task %d unexpected error", task_id)

        db.commit()

    finally:
        db.close()
