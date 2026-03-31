"""
阿里云 OSS 上传服务
"""
from __future__ import annotations

import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_bucket = None


def _get_bucket():
    global _bucket
    if _bucket is not None:
        return _bucket

    import oss2
    from app.config import get_settings
    s = get_settings()

    if not s.OSS_ACCESS_KEY_ID or not s.OSS_ACCESS_KEY_SECRET or not s.OSS_ENDPOINT:
        raise RuntimeError("OSS 配置不完整，请检查 OSS_ACCESS_KEY_ID / OSS_ACCESS_KEY_SECRET / OSS_ENDPOINT")

    auth = oss2.Auth(s.OSS_ACCESS_KEY_ID, s.OSS_ACCESS_KEY_SECRET)
    _bucket = oss2.Bucket(auth, s.OSS_ENDPOINT, s.OSS_BUCKET_NAME)
    return _bucket


def upload_image_bytes(data: bytes, object_key: str, content_type: str = "image/jpeg") -> Optional[str]:
    """将图片字节流上传到 OSS，返回公网访问 URL。"""
    from app.config import get_settings
    s = get_settings()

    try:
        bucket = _get_bucket()
        # inline：浏览器 <img> 内联展示；attachment 会触发强制下载
        filename = object_key.rsplit("/", 1)[-1] if "/" in object_key else object_key
        headers = {
            "Content-Type": content_type,
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "public, max-age=31536000",
        }
        bucket.put_object(object_key, io.BytesIO(data), headers=headers)
        # 拼接公网 URL
        if s.OSS_CDN_DOMAIN:
            domain = s.OSS_CDN_DOMAIN.rstrip("/")
            url = f"{domain}/{object_key}"
        else:
            endpoint = s.OSS_ENDPOINT.rstrip("/")
            # 去掉协议前缀，拼接 bucket 子域名
            if "://" in endpoint:
                scheme, host = endpoint.split("://", 1)
                url = f"{scheme}://{s.OSS_BUCKET_NAME}.{host}/{object_key}"
            else:
                url = f"https://{s.OSS_BUCKET_NAME}.{endpoint}/{object_key}"

        logger.info("OSS upload OK: %s -> %s", object_key, url)
        return url
    except Exception as e:
        logger.error("OSS upload failed [%s]: %s", object_key, e)
        return None


def upload_image_file(file_path: str, object_key: str, content_type: str = "image/jpeg") -> Optional[str]:
    """将本地图片文件上传到 OSS，返回公网访问 URL。"""
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        return upload_image_bytes(data, object_key, content_type)
    except Exception as e:
        logger.error("OSS upload file failed [%s]: %s", file_path, e)
        return None
