"""
采集配置管理接口
用于在线更新 TikTok Cookie 和代理，无需重启服务器。
支持用户独立配置和全局配置两种模式。
"""
import json
import os
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.config import get_settings
from app.core.security import get_current_user
from app.database import SessionLocal
from app.models.user import User
from app.models.user_crawl_config import UserCrawlConfig
from app.schemas.common import Response

router = APIRouter(prefix="/settings", tags=["采集配置"])

_ENV_PATH = Path(__file__).parent.parent.parent.parent / ".env"

# TikTok Shop 已开通的全部国家/区域（与前端 REGION_MAP / utils/index.js 保持一致）
SUPPORTED_REGIONS = ("PH", "MY", "TH", "SG", "ID", "VN")


class CrawlConfig(BaseModel):
    tiktok_cookies: str = ""
    tiktok_proxy: str = ""


class RegionProxies(BaseModel):
    """按国家配置代理：key 为 region code（PH/MY/TH/SG/ID/VN），value 为代理地址，空字符串表示不代理"""
    region_proxies: dict = Field(default_factory=dict)


def _update_env(key: str, value: str) -> None:
    """原地更新 .env 文件中指定 key 的值"""
    if not _ENV_PATH.exists():
        return
    content = _ENV_PATH.read_text(encoding="utf-8")
    pattern = rf"^{key}=.*$"
    replacement = f"{key}={value}"
    if re.search(pattern, content, flags=re.MULTILINE):
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    else:
        content += f"\n{replacement}\n"
    _ENV_PATH.write_text(content, encoding="utf-8")


def _validate_proxy(proxy: str) -> None:
    if proxy and not re.match(r"^(http|socks5)://", proxy):
        raise HTTPException(
            status_code=400,
            detail="代理格式错误，支持 http://user:pass@host:port 或 socks5://host:port",
        )


def _sanitize_region_proxies(raw) -> dict:
    """清洗分国家代理：仅保留 SUPPORTED_REGIONS，去空，统一成 {REGION: proxy_str}。"""
    if not raw or not isinstance(raw, dict):
        return {}
    out: dict = {}
    for region in SUPPORTED_REGIONS:
        val = raw.get(region)
        if isinstance(val, str):
            val = val.strip()
            if val:
                _validate_proxy(val)
                out[region] = val
    return out


@router.get("/crawl", response_model=Response[CrawlConfig], summary="获取当前用户的采集配置")
def get_crawl_config(current_user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        user_config = db.query(UserCrawlConfig).filter(UserCrawlConfig.user_id == current_user.id).first()

        if user_config and (user_config.tiktok_cookies or user_config.tiktok_proxy):
            return Response(data=CrawlConfig(
                tiktok_cookies=user_config.tiktok_cookies or "",
                tiktok_proxy=user_config.tiktok_proxy or "",
            ))

        s = get_settings()
        return Response(data=CrawlConfig(
            tiktok_cookies=s.TIKTOK_COOKIES,
            tiktok_proxy=s.TIKTOK_PROXY,
        ))
    finally:
        db.close()


@router.get("/crawl/region-proxies", response_model=Response[RegionProxies], summary="获取分国家代理配置")
def get_region_proxies(current_user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        user_config = db.query(UserCrawlConfig).filter(UserCrawlConfig.user_id == current_user.id).first()
        proxies = _sanitize_region_proxies(user_config.region_proxies if user_config else None)
        return Response(data=RegionProxies(region_proxies=proxies))
    finally:
        db.close()


@router.post("/crawl/cookies", summary="更新当前用户的 TikTok Cookie")
def update_cookies(
    payload: CrawlConfig,
    current_user: User = Depends(get_current_user),
):
    raw = payload.tiktok_cookies.strip() if payload.tiktok_cookies else ""

    if raw:
        try:
            parsed = json.loads(raw)
            if not isinstance(parsed, (dict, list)):
                raise ValueError
        except (json.JSONDecodeError, ValueError):
            if "=" not in raw:
                raise HTTPException(status_code=400, detail="Cookie 格式错误，请使用 JSON 或 key=value 格式")

    db = SessionLocal()
    try:
        user_config = db.query(UserCrawlConfig).filter(UserCrawlConfig.user_id == current_user.id).first()

        if user_config:
            user_config.tiktok_cookies = raw
        else:
            user_config = UserCrawlConfig(
                user_id=current_user.id,
                tiktok_cookies=raw
            )
            db.add(user_config)

        db.commit()
        return Response(message="Cookie 已更新，下次采集任务将自动使用" if raw else "Cookie 已清除")
    finally:
        db.close()


@router.post("/crawl/proxy", summary="更新当前用户的默认代理（无分国家配置的国家回退使用）")
def update_proxy(
    payload: CrawlConfig,
    current_user: User = Depends(get_current_user),
):
    proxy = payload.tiktok_proxy.strip() if payload.tiktok_proxy else ""
    _validate_proxy(proxy)

    db = SessionLocal()
    try:
        user_config = db.query(UserCrawlConfig).filter(UserCrawlConfig.user_id == current_user.id).first()

        if user_config:
            user_config.tiktok_proxy = proxy
        else:
            user_config = UserCrawlConfig(
                user_id=current_user.id,
                tiktok_proxy=proxy
            )
            db.add(user_config)

        db.commit()

        msg = f"默认代理已设置为 {proxy}" if proxy else "默认代理已清除（直连模式）"
        return Response(message=msg)
    finally:
        db.close()


@router.post("/crawl/region-proxies", response_model=Response[RegionProxies], summary="按国家保存代理配置")
def update_region_proxies(
    payload: RegionProxies,
    current_user: User = Depends(get_current_user),
):
    """批量保存每个 TikTok 国家的代理；未填的国家留空，使用默认代理。"""
    cleaned = _sanitize_region_proxies(payload.region_proxies)

    db = SessionLocal()
    try:
        user_config = db.query(UserCrawlConfig).filter(UserCrawlConfig.user_id == current_user.id).first()

        if user_config:
            user_config.region_proxies = cleaned
        else:
            user_config = UserCrawlConfig(
                user_id=current_user.id,
                region_proxies=cleaned,
            )
            db.add(user_config)

        db.commit()
        return Response(
            data=RegionProxies(region_proxies=cleaned),
            message=f"已保存 {len(cleaned)} 个国家的代理配置",
        )
    finally:
        db.close()


@router.delete("/crawl/cookies", summary="清除当前用户的 Cookie")
def clear_cookies(current_user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        user_config = db.query(UserCrawlConfig).filter(UserCrawlConfig.user_id == current_user.id).first()
        if user_config:
            user_config.tiktok_cookies = ""
            db.commit()
        return Response(message="Cookie 已清除")
    finally:
        db.close()
