"""
采集配置管理接口
用于在线更新 TikTok Cookie 和代理，无需重启服务器。
"""
import json
import os
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import get_settings
from app.schemas.common import Response

router = APIRouter(prefix="/settings", tags=["采集配置"])

_ENV_PATH = Path(__file__).parent.parent.parent.parent / ".env"


class CrawlConfig(BaseModel):
    tiktok_cookies: str = ""
    tiktok_proxy: str = ""


def _update_env(key: str, value: str) -> None:
    """原地更新 .env 文件中指定 key 的值"""
    if not _ENV_PATH.exists():
        return
    content = _ENV_PATH.read_text(encoding="utf-8")
    # 已存在则替换，否则追加
    pattern = rf"^{key}=.*$"
    replacement = f"{key}={value}"
    if re.search(pattern, content, flags=re.MULTILINE):
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    else:
        content += f"\n{replacement}\n"
    _ENV_PATH.write_text(content, encoding="utf-8")


@router.get("/crawl", response_model=Response[CrawlConfig], summary="获取当前采集配置")
def get_crawl_config():
    s = get_settings()
    return Response(data=CrawlConfig(
        tiktok_cookies=s.TIKTOK_COOKIES,
        tiktok_proxy=s.TIKTOK_PROXY,
    ))


@router.post("/crawl/cookies", summary="更新 TikTok Cookie")
def update_cookies(payload: CrawlConfig):
    """
    接受以下格式：
    - JSON 对象:  {"sessionid":"xxx","msToken":"yyy"}
    - Cookie 字符串: sessionid=xxx; msToken=yyy
    """
    raw = payload.tiktok_cookies.strip()
    if not raw:
        raise HTTPException(status_code=400, detail="Cookie 不能为空")

    # 验证格式
    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, (dict, list)):
            raise ValueError
    except (json.JSONDecodeError, ValueError):
        # 尝试 key=value; 格式
        if "=" not in raw:
            raise HTTPException(status_code=400, detail="Cookie 格式错误，请使用 JSON 或 key=value 格式")

    _update_env("TIKTOK_COOKIES", raw)

    # 更新运行时配置（lru_cache 需要手动更新）
    os.environ["TIKTOK_COOKIES"] = raw
    get_settings.cache_clear()

    return Response(message="Cookie 已更新，下次采集任务将自动使用")


@router.post("/crawl/proxy", summary="更新代理配置")
def update_proxy(payload: CrawlConfig):
    proxy = payload.tiktok_proxy.strip()
    if proxy and not re.match(r"^(http|socks5)://", proxy):
        raise HTTPException(
            status_code=400,
            detail="代理格式错误，支持 http://user:pass@host:port 或 socks5://host:port"
        )

    _update_env("TIKTOK_PROXY", proxy)
    os.environ["TIKTOK_PROXY"] = proxy
    get_settings.cache_clear()

    msg = f"代理已设置为 {proxy}" if proxy else "代理已清除（直连模式）"
    return Response(message=msg)


@router.delete("/crawl/cookies", summary="清除 Cookie")
def clear_cookies():
    _update_env("TIKTOK_COOKIES", "")
    os.environ["TIKTOK_COOKIES"] = ""
    get_settings.cache_clear()
    return Response(message="Cookie 已清除")
