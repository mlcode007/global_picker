from typing import List, Optional
from pydantic import BaseModel, field_validator
import re


class SmsSendRequest(BaseModel):
    """发送短信验证码"""
    phone: str
    purpose: str = "login"

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^1[3-9]\d{9}$", v):
            raise ValueError("请输入正确的手机号")
        return v

    @field_validator("purpose")
    @classmethod
    def validate_purpose(cls, v: str) -> str:
        if v not in ("register", "login", "reset_password"):
            raise ValueError("无效的验证码用途")
        return v


class SmsLoginRequest(BaseModel):
    """短信验证码登录"""
    phone: str
    code: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^1[3-9]\d{9}$", v):
            raise ValueError("请输入正确的手机号")
        return v


class UserRegisterRequest(BaseModel):
    """用户注册"""
    phone: str
    code: str
    company_name: str
    contact_name: str = ""
    password: Optional[str] = None
    business_type: str = "cross_border"
    target_regions: Optional[List[str]] = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^1[3-9]\d{9}$", v):
            raise ValueError("请输入正确的手机号")
        return v

    @field_validator("company_name")
    @classmethod
    def validate_company(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) < 2:
            raise ValueError("公司名称至少2个字符")
        return v


class UserLogin(BaseModel):
    """密码登录（兼容老接口）"""
    username: str
    password: str


class UserProfileUpdate(BaseModel):
    """更新用户资料"""
    display_name: Optional[str] = None
    company_name: Optional[str] = None
    contact_name: Optional[str] = None
    business_type: Optional[str] = None
    target_regions: Optional[List[str]] = None
    avatar: Optional[str] = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    phone: Optional[str] = None
    username: Optional[str] = None
    display_name: str
    company_name: str = ""
    contact_name: str = ""
    business_type: str = "cross_border"
    target_regions: Optional[list] = None
    avatar: Optional[str] = None
    role: str
    is_active: int

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
