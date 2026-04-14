from functools import lru_cache
from typing import List
from urllib.parse import quote_plus
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 应用
    APP_ENV: str = "development"
    SECRET_KEY: str = "change_me_in_production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # MySQL
    MYSQL_HOST: str
    MYSQL_PORT: int = 3306
    MYSQL_USER: str
    MYSQL_PASSWORD: str
    MYSQL_DB: str

    # Redis
    REDIS_HOST: str
    REDIS_PORT: int = 6379
    REDIS_USER: str = ""
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0

    # 跨域
    CORS_ORIGINS: List[str] = ["http://localhost:5173"]

    # TikTok 采集配置
    # 代理：格式 http://user:pass@host:port 或 socks5://host:port，留空不使用
    TIKTOK_PROXY: str = ""
    # Cookie：从浏览器 DevTools 复制后粘贴，JSON 格式 {"name":"value",...}
    TIKTOK_COOKIES: str = ""
    # 有头模式：True 显示浏览器窗口（可手动过验证），False 无界面后台运行
    TIKTOK_HEADLESS: bool = True

    # 阿里云 OSS
    OSS_ACCESS_KEY_ID: str = ""
    OSS_ACCESS_KEY_SECRET: str = ""
    OSS_BUCKET_NAME: str = "global-picker-pdd-image"
    OSS_ENDPOINT: str = ""
    # OSS 公网访问域名（留空则自动拼接 bucket.endpoint）
    OSS_CDN_DOMAIN: str = ""

    # 阿里云短信服务
    ALIYUN_SMS_ACCESS_KEY_ID: str = ""
    ALIYUN_SMS_ACCESS_KEY_SECRET: str = ""
    ALIYUN_SMS_SIGN_NAME: str = ""
    ALIYUN_SMS_TEMPLATE_CODE: str = ""
    SMS_CODE_EXPIRE_MINUTES: int = 5
    SMS_CODE_LENGTH: int = 6
    SMS_SEND_INTERVAL_SECONDS: int = 60

    # 拼多多拍照购：在结果页依次点进详情，从 dumpsys 解析 goods_id（约多 4s/条）
    PDD_EXTRACT_PRODUCT_LINKS: bool = True

    @property
    def database_url(self) -> str:
        # quote_plus 对密码中的特殊字符（如 @）进行 URL 编码
        pwd = quote_plus(self.MYSQL_PASSWORD)
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{pwd}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}"
            f"?charset=utf8mb4"
        )

    @property
    def redis_url(self) -> str:
        if self.REDIS_PASSWORD:
            pwd = quote_plus(self.REDIS_PASSWORD)
            return (
                f"redis://:{pwd}@{self.REDIS_HOST}"
                f":{self.REDIS_PORT}/{self.REDIS_DB}"
            )
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
