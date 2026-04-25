"""
TikTok 商品采集器 - 可扩展架构版本

设计目标：
  - 独立脚本，不修改现有代码
  - 统一采集接口，便于后续替换
  - 支持多版本采集策略
  - 自动处理验证码和 Cookie 持久化

使用方式：
  # 直接运行
  python -m app.workers.tiktok_crawler_v2 "https://shop.tiktok.com/view/product/xxx"
  
  # 前端调用（通过 API 路由）
  前端 → API → run_crawl_task → 调度器 → 采集器

扩展方式：
  1. 新增采集策略类，继承 BaseCrawler
  2. 在 CRAWLERS 列表中注册，按优先级排序
  3. 无需修改其他代码
"""
import asyncio
import json
import logging
import re
import shutil
import sys
import tempfile
from abc import ABC, abstractmethod
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional, List, Dict, Any

from playwright.async_api import async_playwright, TimeoutError as PwTimeout
from playwright_stealth import Stealth
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal
from app.models.product import Product
from app.models.user_crawl_config import UserCrawlConfig
from app.models.crawl_task import CrawlTask

logger = logging.getLogger(__name__)

_UA_DESKTOP = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def _update_task_status(task_id: Optional[int], status_detail: str) -> None:
    if not task_id:
        return
    try:
        db = SessionLocal()
        try:
            task = db.query(CrawlTask).filter(CrawlTask.id == task_id).first()
            if task:
                task.status_detail = status_detail
                db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.warning("更新任务状态失败: %s", e)


class BaseCrawler(ABC):
    """采集器基类"""
    name: str = "base"
    priority: int = 999

    @abstractmethod
    async def fetch_product(
        self,
        url: str,
        user_id: Optional[int] = None,
        proxy: Optional[str] = None,
        cookies_str: Optional[str] = None,
        task_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """采集商品数据，返回统一格式的商品信息"""
        pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name} priority={self.priority}>"


class CrawlerDispatcher:
    """采集器调度器 - 按优先级依次尝试"""

    def __init__(self, crawlers: List[BaseCrawler]):
        self.crawlers = sorted(crawlers, key=lambda c: c.priority)

    async def dispatch(
        self,
        url: str,
        user_id: Optional[int] = None,
        proxy: Optional[str] = None,
        cookies_str: Optional[str] = None,
        task_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        logger.info("开始调度采集，共 %d 个采集器: %s", len(self.crawlers), [c.name for c in self.crawlers])

        for crawler in self.crawlers:
            try:
                logger.info("尝试采集器: %s (优先级: %d)", crawler.name, crawler.priority)
                result = await crawler.fetch_product(
                    url=url,
                    user_id=user_id,
                    proxy=proxy,
                    cookies_str=cookies_str,
                    task_id=task_id,
                )
                if result and result.get("title"):
                    logger.info("采集器 %s 成功: %s", crawler.name, result.get("title", "")[:50])
                    result["_crawler"] = crawler.name
                    return result
                else:
                    logger.warning("采集器 %s 未返回有效数据", crawler.name)
            except Exception as e:
                logger.error("采集器 %s 异常: %s", crawler.name, e, exc_info=True)

        logger.error("所有采集器均失败")
        return None


class V2Crawler(BaseCrawler):
    """V2 采集器 - 请求拦截版（当前主力）"""
    name = "v2_intercept"
    priority = 10

    async def fetch_product(
        self,
        url: str,
        user_id: Optional[int] = None,
        proxy: Optional[str] = None,
        cookies_str: Optional[str] = None,
        task_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        settings = get_settings()
        proxy_cfg = proxy or settings.TIKTOK_PROXY
        cookies = self._parse_cookies(cookies_str) if cookies_str else []

        if not cookies and user_id:
            _update_task_status(task_id, "正在读取用户 Cookie 配置...")
            db = SessionLocal()
            try:
                user_config = db.query(UserCrawlConfig).filter(
                    UserCrawlConfig.user_id == user_id
                ).first()
                if user_config and user_config.tiktok_cookies:
                    cookies = self._parse_cookies(user_config.tiktok_cookies)
                    if user_config.tiktok_proxy:
                        proxy_cfg = user_config.tiktok_proxy
            finally:
                db.close()

        if "shop.tiktok.com/view/product/" in url and "locale=" not in url:
            url = f"{url}&locale=zh-CN" if "?" in url else f"{url}?locale=zh-CN"

        intercepted_data = None
        data_ready = asyncio.Event()

        _update_task_status(task_id, "正在启动浏览器...")
        async with async_playwright() as pw:
            headless = settings.TIKTOK_HEADLESS
            launch_opts = {
                "headless": headless,
                "slow_mo": 0 if headless else 200,
                "args": ["--no-sandbox", "--disable-blink-features=AutomationControlled", "--disable-dev-shm-usage"],
            }
            if proxy_cfg:
                launch_opts["proxy"] = {"server": proxy_cfg}

            browser = await pw.chromium.launch(**launch_opts)
            context = await browser.new_context(
                user_agent=_UA_DESKTOP,
                locale="en-PH",
                timezone_id="Asia/Manila",
                viewport={"width": 1280, "height": 900},
                extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
            )

            if cookies:
                await context.add_cookies(cookies)
                logger.info("已注入 %d 条 Cookie", len(cookies))
                _update_task_status(task_id, "已注入 Cookie，正在打开商品页面...")

            page = await context.new_page()
            await Stealth().apply_stealth_async(page)

            async def on_request(request):
                nonlocal intercepted_data
                if "__loader=" in request.url and "__ssrDirect=true" in request.url:
                    logger.info("拦截到目标请求: %s", request.url[:100])
                    try:
                        response = await request.response()
                        if response:
                            body = await response.body()
                            body_str = body.decode("utf-8", errors="ignore")
                            logger.info("响应体长度: %d 字符", len(body_str))
                            try:
                                json_data = json.loads(body_str)
                                if isinstance(json_data, dict):
                                    intercepted_data = json_data
                                    logger.info("成功解析 JSON 响应, keys: %s", list(intercepted_data.keys())[:10])
                                    _update_task_status(task_id, "成功拦截到商品数据")
                                    data_ready.set()
                                    return
                            except json.JSONDecodeError:
                                pass
                            intercepted_data = self._extract_remix_context(body_str)
                            if intercepted_data:
                                logger.info("从 HTML 中提取 remixContext, keys: %s", list(intercepted_data.keys())[:10])
                                _update_task_status(task_id, "从页面中提取到商品数据")
                                data_ready.set()
                            else:
                                logger.warning("未能提取任何数据")
                    except Exception as e:
                        logger.warning("拦截处理失败: %s", e, exc_info=True)

            page.on("request", on_request)

            _update_task_status(task_id, "正在打开 TikTok 商品页面...")
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            except PwTimeout:
                logger.warning("页面加载超时")
                _update_task_status(task_id, "页面加载超时")
            except Exception as e:
                logger.warning("页面加载异常: %s", e)
                _update_task_status(task_id, "页面加载异常")
            
            if intercepted_data:
                logger.info("数据已在页面加载时拦截成功，直接退出")
                _update_task_status(task_id, "商品数据已获取")
                await browser.close()
            else:
                _update_task_status(task_id, "页面已加载，等待数据请求...")
                try:
                    await asyncio.wait_for(data_ready.wait(), timeout=15)
                    logger.info("数据拦截成功，提前退出")
                    _update_task_status(task_id, "商品数据已获取")
                except asyncio.TimeoutError:
                    logger.warning("等待数据超时，检查页面状态")
                    
                    title = await page.title()
                    title_lower = title.lower()
                    
                    if "security" in title_lower or "captcha" in title_lower:
                        logger.warning("触发验证码")
                        _update_task_status(task_id, "触发验证码，正在处理...")
                        for attempt in range(2):
                            logger.info("自动处理验证码 %d/2", attempt + 1)
                            _update_task_status(task_id, f"正在处理验证码 ({attempt + 1}/2)...")
                            if await self._solve_captcha(page, context):
                                logger.info("验证码通过，等待数据...")
                                _update_task_status(task_id, "验证码通过，等待数据...")
                                try:
                                    await asyncio.wait_for(data_ready.wait(), timeout=15)
                                    _update_task_status(task_id, "商品数据已获取")
                                    break
                                except asyncio.TimeoutError:
                                    logger.warning("验证码后等待数据超时")
                            if attempt < 1:
                                try:
                                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                                except Exception:
                                    await asyncio.sleep(2)
                        else:
                            if not headless:
                                logger.warning("等待手动完成验证码（60s）")
                                _update_task_status(task_id, "等待手动完成验证码（60秒）...")
                                try:
                                    await page.wait_for_function(
                                        """() => {
                                            const t = document.title.toLowerCase();
                                            return !t.includes('security') && !t.includes('captcha') && t.length > 0;
                                        }""",
                                        timeout=60000,
                                    )
                                except PwTimeout:
                                    await browser.close()
                                    raise RuntimeError("验证码超时")
                            else:
                                await browser.close()
                                raise RuntimeError("验证码未通过")
                    else:
                        logger.info("页面标题: %s，未检测到验证码", title)
                        await asyncio.sleep(2)
                
                await browser.close()

        if intercepted_data:
            _update_task_status(task_id, "正在解析商品数据...")
            logger.info("开始解析商品数据")
            product_data = self._parse_product_data(intercepted_data)
            if product_data:
                logger.info("解析成功: %s", product_data.get("title", "")[:50])
                _update_task_status(task_id, "商品数据解析成功")
                return product_data
            else:
                logger.warning("解析失败: remixContext 中未找到商品信息")
                _update_task_status(task_id, "解析失败：未找到商品信息")
        else:
            logger.warning("未拦截到任何数据")
            _update_task_status(task_id, "未拦截到任何数据")
        
        return None

    def _parse_cookies(self, raw: str) -> List[Dict[str, str]]:
        if not raw.strip():
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
            for pair in raw.split(";"):
                pair = pair.strip()
                if "=" in pair:
                    name, _, value = pair.partition("=")
                    cookies.append({
                        "name": name.strip(), "value": value.strip(),
                        "domain": ".tiktok.com", "path": "/",
                    })
        return cookies

    def _extract_remix_context(self, html: str) -> Optional[Dict[str, Any]]:
        patterns = [
            r'window\.__remixContext\s*=\s*(\{.*?\})\s*;',
            r'window\.__remixContext\s*=\s*(\{[\s\S]*?\})\s*;',
            r'window\.__remixContext\s*=\s*(\{.*?\})\s*</script>',
            r'(\{"loaderData"[\s\S]*?\})\s*[;,<]',
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.MULTILINE | re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    continue
        return None

    def _parse_product_data(self, remix_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not remix_data or not isinstance(remix_data, dict):
            logger.warning("remix_data 为空或不是字典")
            return None

        page_config = remix_data.get("page_config")
        if not page_config:
            for key, val in remix_data.items():
                if isinstance(val, dict) and "page_config" in val:
                    page_config = val.get("page_config")
                    break

        if not page_config or not isinstance(page_config, dict):
            logger.warning("未找到 page_config, remix_data keys: %s", list(remix_data.keys())[:10])
            return None

        components = page_config.get("components_map", [])
        if not isinstance(components, list):
            logger.warning("components_map 不是列表")
            return None

        logger.info("components_map 共 %d 个组件", len(components))

        product_component = None
        for comp in components:
            if isinstance(comp, dict) and comp.get("component_type") == "product_info":
                product_component = comp
                break

        if not product_component:
            logger.warning("未找到 product_info 组件, 组件类型: %s", [c.get("component_type") for c in components if isinstance(c, dict)][:10])
            return None

        cd = product_component.get("component_data") or {}
        pi = cd.get("product_info") or {}
        pm = pi.get("product_model") or {}

        if not pm.get("product_id"):
            logger.warning("未找到 product_id, pm keys: %s", list(pm.keys())[:10] if pm else "pm为空")
            return None

        logger.info("找到商品: product_id=%s, name=%s", pm.get("product_id"), pm.get("name", "")[:50])

        images_raw = pm.get("images") or []
        image_urls = []
        for img in images_raw[:10]:
            urls = img.get("url_list") or []
            if urls:
                image_urls.append(urls[0])

        promo = pi.get("promotion_model") or {}
        promo_price = self._dig(promo, "promotion_product_price", "min_price") or {}

        logger.info("promo_price keys: %s", list(promo_price.keys())[:10] if promo_price else "promo_price为空")

        price_val = (
            promo_price.get("sale_price_decimal")
            or promo_price.get("single_product_price_decimal")
            or promo_price.get("sale_price_format")
        )
        original_price_val = (
            promo_price.get("origin_price_decimal")
            or promo_price.get("origin_price_format")
        )
        currency = promo_price.get("currency_name")

        logger.info("解析价格: price=%s, currency=%s, sold_count=%s", price_val, currency, pm.get("sold_count"))

        logistics_list = promo.get("promotion_logistic_list") or []
        logistics = logistics_list[0] if logistics_list else {}
        ship_fee_obj = logistics.get("shippingFee") or {}

        review = pi.get("review_model") or {}
        seller = pi.get("seller_model") or {}

        category_info = cd.get("category_info") or {}
        categories = category_info.get("recommended_categories") or []
        category_name = categories[0].get("category_name") if categories else None

        real_region = remix_data.get("region_info", {}).get("real_region")

        result = {
            "product_id": pm.get("product_id"),
            "title": pm.get("name"),
            "description": pm.get("description"),
            "images": image_urls,
            "sold_count": pm.get("sold_count"),
            "price": price_val,
            "currency": currency,
            "original_price": original_price_val,
            "discount": promo_price.get("discount_format"),
            "rating": review.get("product_overall_score"),
            "review_count": review.get("product_review_count"),
            "shop_name": seller.get("shop_name"),
            "shop_id": str(pm.get("seller_id", "")) if pm.get("seller_id") else None,
            "shipping_fee": self._dig(ship_fee_obj, "origin_price"),
            "shipping_currency": ship_fee_obj.get("currency"),
            "free_shipping": logistics.get("freeShipping"),
            "category": category_name,
            "region": real_region,
        }
        return result

    def _dig(self, data: Any, *keys: str) -> Any:
        for key in keys:
            if not isinstance(data, dict):
                return None
            data = data.get(key)
        return data

    async def _solve_captcha(self, page, context) -> bool:
        try:
            root = Path(__file__).resolve().parent.parent / "spider" / "tiktok_product"
            p = str(root)
            if p not in sys.path:
                sys.path.insert(0, p)
            
            from tiktok_captcha_solver import TikTokCaptchaSolver

            tmp = tempfile.mkdtemp(prefix="tt_captcha_")
            try:
                solver = TikTokCaptchaSolver(download_dir=tmp, cookies_file=f"{tmp}/cookies.json")
                solver.page = page
                solver.context = context

                await asyncio.sleep(2)

                try:
                    await page.wait_for_selector("#captcha-verify-image", state="visible", timeout=20000)
                except PwTimeout:
                    logger.warning("验证码背景图未出现")

                if not await solver.check_captcha_exists():
                    title = (await page.title()).lower()
                    if "security" not in title and "captcha" not in title:
                        logger.info("页面已非验证码状态")
                        return True
                    return False

                await solver.get_captcha_images()
                distance = solver.calculate_slide_distance()
                if distance <= 0:
                    logger.warning("滑块距离计算失败")
                    return False

                await solver.drag_slider(distance)

                try:
                    await page.wait_for_function(
                        """() => {
                            const t = document.title.toLowerCase();
                            if (document.querySelector('.secsdk-captcha-drag-success')) return true;
                            return !t.includes('security') && !t.includes('captcha') && t.length > 0;
                        }""",
                        timeout=90000,
                    )
                except PwTimeout:
                    logger.warning("验证码通过超时")

                try:
                    await page.wait_for_load_state("networkidle", timeout=25000)
                except PwTimeout:
                    pass

                title = (await page.title()).lower()
                if "security" in title or "captcha" in title:
                    logger.warning("验证码未通过")
                    return False

                logger.info("验证码已通过")
                return True
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
        except Exception as e:
            logger.warning("验证码处理失败: %s", e)
            return False

    async def _persist_cookies(self, user_id: int, context) -> None:
        if not user_id:
            return
        try:
            pw_cookies = await context.cookies()
        except Exception as e:
            logger.warning("读取浏览器 Cookie 失败，无法回写用户表: %s", e)
            return

        new_kv = {}
        for c in pw_cookies:
            dom = (c.get("domain") or "").lower()
            name = c.get("name")
            if not name:
                continue
            if any(k in dom for k in ("tiktok.com", "tiktokcdn", "ttwstatic", "byteoversea", "tiktokv.com")):
                new_kv[str(name)] = str(c.get("value", ""))

        if not new_kv:
            logger.info("浏览器中无 TikTok 相关 Cookie，跳过回写用户表")
            return

        db = SessionLocal()
        try:
            cfg = db.query(UserCrawlConfig).filter(UserCrawlConfig.user_id == user_id).first()
            base: Dict[str, str] = {}
            if cfg and cfg.tiktok_cookies:
                try:
                    data = json.loads(cfg.tiktok_cookies)
                    if isinstance(data, dict):
                        base = data
                except json.JSONDecodeError:
                    pass
            base.update(new_kv)
            merged = json.dumps(base, ensure_ascii=False)
            if cfg:
                cfg.tiktok_cookies = merged
            else:
                db.add(UserCrawlConfig(user_id=user_id, tiktok_cookies=merged))
            db.commit()
            logger.info("已合并并更新用户 %d 的 tiktok_cookies（共 %d 个键）", user_id, len(json.loads(merged)))
        except Exception as e:
            logger.warning("写入 user_crawl_configs.tiktok_cookies 失败: %s", e)
            db.rollback()
        finally:
            db.close()


# 注册采集器 - 后续新增采集器只需添加到这里
CRAWLERS = [
    V2Crawler(),
    # 未来新增采集器示例：
    # V3Crawler(),  # priority=5 会优先尝试
]

dispatcher = CrawlerDispatcher(CRAWLERS)


def _safe_decimal(val) -> Optional[Decimal]:
    try:
        if val is None:
            return None
        s = str(val).strip()
        if not s:
            return None
        if re.fullmatch(r"-?\d+", s):
            return Decimal(s)
        s2 = re.sub(r"[^\d.,-]", "", s)
        if not s2 or s2 == "-":
            return None
        neg = s2.startswith("-")
        if neg:
            s2 = s2[1:]
        if s2.count(".") > 1:
            digits = re.sub(r"[^\d]", "", s2)
            if not digits:
                return None
            d = Decimal(digits)
            return -d if neg else d
        if s2.count(",") > 1:
            digits = re.sub(r"[^\d]", "", s2)
            if not digits:
                return None
            d = Decimal(digits)
            return -d if neg else d
        if "," in s2 and "." in s2:
            last = max(s2.rfind(","), s2.rfind("."))
            if s2[last] == ".":
                d = Decimal(s2.replace(",", ""))
            else:
                d = Decimal(s2.replace(".", "").replace(",", "."))
            return -d if neg else d
        if "," in s2:
            parts = s2.split(",")
            if len(parts) == 2 and len(parts[1]) <= 2:
                d = Decimal(parts[0].replace(".", "") + "." + parts[1])
            else:
                d = Decimal(re.sub(r"[^\d]", "", s2))
            return -d if neg else d
        d = Decimal(s2)
        return -d if neg else d
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


def _save_to_database(
    product_data: Dict[str, Any],
    url: str,
    user_id: Optional[int] = None,
    crawl_task_id: Optional[int] = None,
) -> Product:
    db = SessionLocal()
    try:
        existing = db.query(Product).filter(
            Product.user_id == user_id,
            Product.is_deleted == 0,
            Product.tiktok_product_id == product_data.get("product_id"),
        ).first()

        if existing:
            product = existing
            logger.info("更新现有商品: %s", product_data.get("title", "")[:50])
        else:
            product = Product(
                user_id=user_id,
                crawl_task_id=crawl_task_id,
                tiktok_url=url,
                tiktok_product_id=product_data.get("product_id"),
            )
            db.add(product)
            logger.info("创建新商品: %s", product_data.get("title", "")[:50])

        product.title = (product_data.get("title") or "")[:512]
        product.description = product_data.get("description")
        product.price = _safe_decimal(product_data.get("price")) or Decimal("0")
        product.currency = (product_data.get("currency") or "PHP")[:8]
        product.original_price = _safe_decimal(product_data.get("original_price"))
        product.discount = (product_data.get("discount") or "")[:16]
        product.sales_volume = _safe_int(product_data.get("sold_count")) or 0
        product.rating = _safe_decimal(product_data.get("rating"))
        product.review_count = _safe_int(product_data.get("review_count")) or 0
        product.shop_name = (product_data.get("shop_name") or "")[:256]
        product.shop_id = (product_data.get("shop_id") or "")[:64]
        product.region = (product_data.get("region") or "PH")[:16]
        product.shipping_fee = _safe_decimal(product_data.get("shipping_fee"))
        product.free_shipping = 1 if product_data.get("free_shipping") else 0
        product.category = (product_data.get("category") or "")[:128]

        images = product_data.get("images") or []
        if images:
            product.main_image_url = images[0]
            product.image_urls = images[:20]

        from app.services.exchange_rate_service import convert_to_cny
        if product.price and product.currency:
            cny = convert_to_cny(db, product.price, product.currency)
            if cny is not None:
                product.price_cny = cny

        db.commit()
        db.refresh(product)
        logger.info("商品保存成功, ID: %s", product.id)
        return product
    except Exception as e:
        db.rollback()
        logger.error("保存商品失败: %s", e, exc_info=True)
        raise
    finally:
        db.close()


async def crawl_tiktok_product(
    url: str,
    user_id: Optional[int] = None,
    crawl_task_id: Optional[int] = None,
    proxy: Optional[str] = None,
    cookies_str: Optional[str] = None,
) -> Dict[str, Any]:
    """
    TikTok 商品采集主函数
    
    参数:
        url: TikTok 商品链接
        user_id: 用户ID（用于读取用户配置）
        crawl_task_id: 采集任务ID
        proxy: 代理服务器地址
        cookies_str: Cookie 字符串
    
    返回:
        {
            "success": bool,
            "product_id": int,
            "data": dict,
            "message": str
        }
    """
    try:
        logger.info("开始采集: %s", url[:80])
        _update_task_status(crawl_task_id, "开始采集任务...")
        
        product_data = await dispatcher.dispatch(
            url=url,
            user_id=user_id,
            proxy=proxy,
            cookies_str=cookies_str,
            task_id=crawl_task_id,
        )

        if not product_data or not product_data.get("title"):
            _update_task_status(crawl_task_id, "采集失败：未获取到商品数据")
            return {
                "success": False,
                "product_id": None,
                "data": None,
                "message": "所有采集器均未采集到商品数据",
            }

        _update_task_status(crawl_task_id, "正在保存商品数据到数据库...")
        product = _save_to_database(
            product_data=product_data,
            url=url,
            user_id=user_id,
            crawl_task_id=crawl_task_id,
        )

        _update_task_status(crawl_task_id, "采集完成")
        return {
            "success": True,
            "product_id": product.id,
            "data": {
                "tiktok_product_id": product.tiktok_product_id,
                "title": product.title,
                "price": str(product.price),
                "currency": product.currency,
                "crawler": product_data.get("_crawler"),
            },
            "message": "采集成功",
        }

    except Exception as e:
        logger.error("采集失败: %s", e, exc_info=True)
        return {
            "success": False,
            "product_id": None,
            "data": None,
            "message": str(e),
        }


async def run_crawl_task(task_id: int) -> None:
    """
    后台任务入口 - 兼容现有 API 路由
    
    参数:
        task_id: 采集任务ID
    """
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

        product_id_match = re.search(r"/product/(\d+)", task.url)
        region_match = re.search(r"[?&]region=([A-Z]{2,3})", task.url)
        
        product_id = product_id_match.group(1) if product_id_match else None
        region = region_match.group(1) if region_match else "PH"

        if not product_id:
            task.status = "failed"
            task.error_msg = "无法从链接中提取商品ID，请确认链接格式"
            db.commit()
            return

        product.tiktok_product_id = product_id
        product.region = region

        old_price = product.price
        old_price_cny = product.price_cny

        try:
            result = await crawl_tiktok_product(
                url=task.url,
                user_id=product.user_id,
                crawl_task_id=task.id,
            )

            if result["success"]:
                task.status = "done"
                task.error_msg = None
                logger.info("crawl task %d done (product_id=%s, user_id=%s)", 
                           task_id, product_id, product.user_id)
            else:
                task.status = "failed"
                task.error_msg = result.get("message", "采集失败")
                task.retry_count += 1

        except RuntimeError as e:
            task.status = "failed"
            task.error_msg = str(e)
            task.retry_count += 1
        except Exception as e:
            task.status = "failed"
            task.error_msg = str(e)[:500]
            task.retry_count += 1
            logger.exception("crawl task %d unexpected error", task_id)

        task.status_detail = None
        db.commit()

    finally:
        db.close()


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if len(sys.argv) < 2:
        print("用法: python -m app.workers.tiktok_crawler_v2 <url> [user_id]")
        sys.exit(1)

    url = sys.argv[1]
    user_id = int(sys.argv[2]) if len(sys.argv) > 2 else None

    result = asyncio.run(crawl_tiktok_product(url, user_id=user_id))
    
    print("\n" + "=" * 60)
    print(f"采集结果: {'成功' if result['success'] else '失败'}")
    print(f"消息: {result['message']}")
    if result['data']:
        print(f"商品ID: {result['product_id']}")
        print(f"标题: {result['data']['title']}")
        print(f"价格: {result['data']['price']} {result['data']['currency']}")
        print(f"采集器: {result['data'].get('crawler', 'unknown')}")
    print("=" * 60)
