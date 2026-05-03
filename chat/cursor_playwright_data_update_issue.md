# Playwright data update issue
_Exported on 2026/4/30 at GMT+8 10:55:55 from Cursor (3.1.17)_

---

**User**

playwright 采集价格等字段没有更新数据?

---

**Cursor**

正在分析项目中 Playwright 采集价格等字段的逻辑，找出数据未更新的原因。



定位到根本原因：Layer0（Remix `loaderData`）只要有 `title` 就会采用该数据并跳过后续 Layer1/Layer3，但 Remix 首屏 hydration 可能含占位价（0）或未填充的销量；`_apply_product_data` 会把解析出的 `0` 当作有效值写入数据库。正在实现：在弱字段时用 DOM 补全并可选等待价格选择器出现。



正在实现：在 Layer0 命中但价格/销量为占位时，等待价格节点并用 DOM（及必要时用拦截的 API）补全字段。



## 原因说明

采集逻辑在 `backend/app/workers/tiktok_crawler.py` 里大致是 **Layer0（Remix `loaderData`）→ Layer1（拦截 API）→ Layer2（window）→ Layer3（DOM）**。

问题在于：**只要 Layer0 里已经有 `title`，就会整包采用 Remix 数据并直接结束**，不再跑 DOM。而 TikTok PDP 首屏 hydration 里经常出现 **占位价 `0`、销量 `0`**，等异步把真实价、销量写进页面时，采集已经结束了。于是库里就出现你截图里的 **PHP/MYR 0.00、销量 0**；评分有时来自别的字段所以还能有数。

另外，`_apply_product_data` 里对销量是 `if n is not None` 就写入，**`0` 会被当成合法整数写进数据库**，会把以前的正确销量覆盖掉。

## 已做修改

在同一文件里增加了 **「弱字段补全」**：

1. 在已有 `product_data`（例如 Layer0 已命中）但 **价格为 0/空、销量为 0/空、或没有评分** 时：
   - 先 **`wait_for_selector` 最多 8s** 等价格相关节点出现；
   - 再跑一次 **`_scrape_dom`**，把 **非空的价、非 0 的销量、评分** 合并进结果；
2. 若价格仍无效，再遍历 **已拦截的 JSON**，用 `_extract_from_api_json` 里 **非 0 的价** 补一次。

这样 Layer0 仍负责标题、图片等主体信息，**价/量/评分** 在占位情况下会尽量从 DOM 或拦截 API 拉回真实展示值。

---

**若仍偶发 0**：再检查 **Cookie/代理/无头 CAPTCHA**（未登录或验证页时 DOM 也可能是空的）。可对单条商品看 `logs` 里是否出现 `弱字段补全：price 来自 DOM` 等日志以确认补全是否生效。需要的话我可以帮你在本机跑一次指定 `task_id` 的采集对照日志。

---

**User**

抽取价格代码在哪

---

**Cursor**

价格抽取主要都在 **`backend/app/workers/tiktok_crawler.py`**，分几条路径：

### 1. DOM 选择器列表（Layer3）

```61:78:backend/app/workers/tiktok_crawler.py
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
```

### 2. DOM 里读价格 + JS 兜底（`_scrape_dom`）

- `first_text(_SELECTORS["price"], "price")` 命中后写入 `result["price"]`
- 下面还有一段 `page.evaluate` 在页面上扫带货币符号的文本作为兜底（约 650–688 行）

### 3. Remix / API 里的价格（Layer0）

新版组件里从 `promotion_product_price` / `min_price` 等取数：

```492:505:backend/app/workers/tiktok_crawler.py
        promo = pi.get("promotion_model") or {}
        promo_price = _dig(promo, "promotion_product_price", "min_price") or {}

        # 优先 API 数值字段；sale_price_format 在 VND 下为「9.319.000」千分位点号，直接 Decimal 会失败→0
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
```

旧版 `initialData` 里从 SKU 的 `real_price` 取（约 574–584 行）。

### 4. 解析数字与币种归一（写入库前）

- `_safe_decimal`：把字符串转成 `Decimal`（约 174–220 行）
- `_normalize_tiktok_price_amount`：按币种处理「分」等大整数（约 230–237 行）
- `_apply_product_data`：从 `data` 里取 `price` / `salePrice` / `priceInfo` 等写入 `product.price`（约 752–765 行）

### 5. Playwright 流程里何时用哪一层

在 **`_fetch_with_playwright`** 里：先 Remix → 再拦截 API → 再 window → 再 DOM；你之前加的弱字段会用 DOM/API 再补一次价格。

如果你说的是 **扩展/前端** 里抽价，可以说一下是哪个目录（例如 `chrome-extension`），我可以再帮你精确到文件。

---

**User**

入库时什么数据库

表

---

**Cursor**

## 用的什么库

入库走的是 **MySQL**（驱动 **PyMySQL**），连接串在配置里拼成 `mysql+pymysql://...`，见：

```19:24:backend/app/config.py
    # MySQL
    MYSQL_HOST: str
    MYSQL_PORT: int = 3306
    MYSQL_USER: str
    MYSQL_PASSWORD: str
    MYSQL_DB: str
```

```64:71:backend/app/config.py
    @property
    def database_url(self) -> str:
        # quote_plus 对密码中的特殊字符（如 @）进行 URL 编码
        pwd = quote_plus(self.MYSQL_PASSWORD)
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{pwd}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}"
            f"?charset=utf8mb4"
        )
```

`database.py` 里用 SQLAlchemy 的 `create_engine(settings.database_url)` 连的就是这个库。

---

## 主要表名（`__tablename__`）

| 表名 | 说明（大致） |
|------|----------------|
| `products` | 商品主表（TikTok 价、销量、评分等写在这里） |
| `crawl_tasks` | 采集任务 |
| `user_crawl_configs` | 用户 TikTok 代理/Cookie 等 |
| `users` | 用户 |
| `pdd_matches` | 拼多多匹配 |
| `profit_records` | 利润记录 |
| `exchange_rates` | 汇率 |
| `photo_search_tasks` | 拍照搜任务 |
| `device_action_logs` | 设备操作日志 |
| `device_pool` | 设备池 |
| `cloud_phone_pool` | 云手机池 |
| `user_cloud_phone` | 用户云手机 |
| `sms_verification` | 短信验证码 |
| `user_points` / `points_transaction` | 积分 |
| `user_quotas` / `collection_history` | 配额/采集历史 |

TikTok Playwright 采完更新的是 **`products`**（以及任务状态在 **`crawl_tasks`**）。库名由环境变量 **`MYSQL_DB`** 决定。

---

**User**

@tiktok_crawler.py 采集完成数据报存代码在什么地方

---

**Cursor**

采集结果写入数据库的逻辑在 **`run_crawl_task`** 里，不在 `_fetch_with_playwright`（后者只返回内存里的 `dict`）。

### 1. 入口：后台任务里拿 Session、查任务和商品

```1226:1240:backend/app/workers/tiktok_crawler.py
async def run_crawl_task(task_id: int) -> None:
    db = SessionLocal()
    try:
        task: Optional[CrawlTask] = (
            db.query(CrawlTask).filter(CrawlTask.id == task_id).first()
        )
        ...
        product: Optional[Product] = (
            db.query(Product).filter(Product.crawl_task_id == task_id).first()
        )
```

### 2. 把采集结果写到 ORM 对象：`products` 行

```1262:1276:backend/app/workers/tiktok_crawler.py
        try:
            data = await _fetch_with_playwright(
                task.url, user_id=product.user_id, task_id=task.id
            )

            if data:
                _apply_product_data(product, data, db=db)
                if _tiktok_price_changed(old_price, old_price_cny, product):
                    from app.services.pdd_service import refresh_product_profit_from_primary_pdd

                    refresh_product_profit_from_primary_pdd(db, product.id)
                task.status = "done"
                task.error_msg = None
```

- **`_apply_product_data(product, data, db=db)`**：把 `data` 里的标题、价格、销量等赋给 **`Product`**（对应表 **`products`**）。函数定义在文件前面约 **`_apply_product_data`**（你之前看过的 739 行一带）。

### 3. 真正提交到 MySQL：`db.commit()`

```1293:1297:backend/app/workers/tiktok_crawler.py
        task.status_detail = None
        db.commit()

    finally:
        db.close()
```

这里一次 **`db.commit()`** 会把本任务里改过的 **`Product`** 和 **`CrawlTask`**（状态、`error_msg` 等）一起刷进数据库。

---

**小结**：保存路径是 **`run_crawl_task` → `_apply_product_data` 改 `product` → 末尾 `db.commit()`**；若 TikTok 价变了，中间还会调 **`refresh_product_profit_from_primary_pdd`** 更新利润相关数据（具体写哪些表在 `pdd_service` 里）。

