"""
阿里云短信服务 + 验证码管理
"""
import hashlib
import hmac
import json
import logging
import random
import string
import uuid
from base64 import b64encode
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urlencode

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.sms_verification import SmsVerification

logger = logging.getLogger(__name__)
settings = get_settings()


def _generate_code(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))


def _percent_encode(s: str) -> str:
    return quote(s, safe="")


def _sign(params: dict, access_key_secret: str) -> str:
    """计算阿里云 API 签名（SignatureMethod=HMAC-SHA1）"""
    sorted_params = sorted(params.items())
    query_string = urlencode(sorted_params, quote_via=quote)
    string_to_sign = f"GET&{_percent_encode('/')}&{_percent_encode(query_string)}"
    h = hmac.new(
        (access_key_secret + "&").encode("utf-8"),
        string_to_sign.encode("utf-8"),
        hashlib.sha1,
    )
    return b64encode(h.digest()).decode("utf-8")


def send_sms_via_aliyun(phone: str, code: str) -> bool:
    """通过阿里云 SMS API 发送验证码"""
    if not settings.ALIYUN_SMS_ACCESS_KEY_ID:
        logger.warning("阿里云短信未配置，跳过实际发送，验证码: %s -> %s", phone, code)
        return True

    params = {
        "AccessKeyId": settings.ALIYUN_SMS_ACCESS_KEY_ID,
        "Action": "SendSms",
        "Format": "JSON",
        "PhoneNumbers": phone,
        "RegionId": "cn-hangzhou",
        "SignName": settings.ALIYUN_SMS_SIGN_NAME,
        "SignatureMethod": "HMAC-SHA1",
        "SignatureNonce": str(uuid.uuid4()),
        "SignatureVersion": "1.0",
        "TemplateCode": settings.ALIYUN_SMS_TEMPLATE_CODE,
        "TemplateParam": json.dumps({"code": code}),
        "Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "Version": "2017-05-25",
    }
    params["Signature"] = _sign(params, settings.ALIYUN_SMS_ACCESS_KEY_SECRET)

    try:
        resp = httpx.get("https://dysmsapi.aliyuncs.com/", params=params, timeout=10)
        result = resp.json()
        if result.get("Code") == "OK":
            logger.info("短信发送成功: %s", phone)
            return True
        logger.error("短信发送失败: %s -> %s", phone, result)
        return False
    except Exception as e:
        logger.error("短信发送异常: %s -> %s", phone, e)
        return False


def can_send_sms(db: Session, phone: str, purpose: str) -> tuple[bool, str]:
    """检查是否可以发送短信（频率限制）"""
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=settings.SMS_SEND_INTERVAL_SECONDS)
    recent = (
        db.query(SmsVerification)
        .filter(
            SmsVerification.phone == phone,
            SmsVerification.purpose == purpose,
            SmsVerification.created_at >= cutoff,
        )
        .first()
    )
    if recent:
        return False, f"发送太频繁，请{settings.SMS_SEND_INTERVAL_SECONDS}秒后再试"
    return True, ""


def create_and_send_code(db: Session, phone: str, purpose: str) -> tuple[bool, str, str]:
    """生成验证码、存库、发送短信。返回 (成功, 消息, 验证码-仅开发模式)"""
    ok, msg = can_send_sms(db, phone, purpose)
    if not ok:
        return False, msg, ""

    code = _generate_code(settings.SMS_CODE_LENGTH)
    expired_at = datetime.now(timezone.utc) + timedelta(minutes=settings.SMS_CODE_EXPIRE_MINUTES)

    record = SmsVerification(
        phone=phone,
        code=code,
        purpose=purpose,
        expired_at=expired_at,
    )
    db.add(record)
    db.commit()

    sent = send_sms_via_aliyun(phone, code)
    is_dev = settings.APP_ENV == "development"

    if not sent:
        if is_dev:
            logger.warning("开发模式：短信未实际发送，验证码 %s -> %s", phone, code)
            return True, "验证码已生成（开发模式，已自动填入）", code
        return False, "短信发送失败，请稍后重试", ""

    return True, "验证码已发送", code if is_dev else ""


def verify_code(db: Session, phone: str, code: str, purpose: str) -> tuple[bool, str]:
    """校验验证码"""
    now = datetime.now(timezone.utc)
    record = (
        db.query(SmsVerification)
        .filter(
            SmsVerification.phone == phone,
            SmsVerification.code == code,
            SmsVerification.purpose == purpose,
            SmsVerification.is_used == 0,
            SmsVerification.expired_at >= now,
        )
        .order_by(SmsVerification.created_at.desc())
        .first()
    )
    if not record:
        return False, "验证码错误或已过期"

    record.is_used = 1
    db.commit()
    return True, ""
