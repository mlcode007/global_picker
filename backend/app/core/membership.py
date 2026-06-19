"""会员系统常量配置"""

TIER_LIMITS = {
    "free":  {"daily_collect": 50},
    "basic": {"daily_collect": 500},
    "pro":   {"daily_collect": 999999},
}

CLOUD_PHONE_PRICE = 100  # 元/月/台
CLOUD_PHONE_MAX = 5      # 每用户最多5台
CLOUD_PHONE_PERIOD_DAYS = 30       # 开通/续费周期（天）
CLOUD_PHONE_RENEW_WARN_DAYS = 7    # 临期提醒阈值（天）

# 每日配额按北京时间（UTC+8）0点重置
QUOTA_TIMEZONE = "Asia/Shanghai"

# 会员价格（元/月）
MEMBERSHIP_PRICES = {
    "basic": 99,
    "pro": 129,
}
