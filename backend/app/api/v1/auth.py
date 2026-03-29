from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.common import Response
from app.schemas.user import (
    SmsSendRequest,
    SmsLoginRequest,
    UserRegisterRequest,
    UserLogin,
    UserProfileUpdate,
    TokenOut,
    UserOut,
    LoginResponse,
)
from app.core.security import (
    verify_password,
    create_access_token,
    hash_password,
    get_current_user,
)
from app.services import sms_service

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/sms/send", summary="发送短信验证码")
def send_sms_code(data: SmsSendRequest, db: Session = Depends(get_db)):
    if data.purpose == "register":
        existing = db.query(User).filter(User.phone == data.phone, User.is_active == 1).first()
        if existing:
            raise HTTPException(status_code=400, detail="该手机号已注册")
    elif data.purpose == "login":
        existing = db.query(User).filter(User.phone == data.phone, User.is_active == 1).first()
        if not existing:
            raise HTTPException(status_code=400, detail="该手机号未注册")

    ok, msg, dev_code = sms_service.create_and_send_code(db, data.phone, data.purpose)
    if not ok:
        raise HTTPException(status_code=429, detail=msg)

    resp_data = {"dev_code": dev_code} if dev_code else None
    return Response(message=msg, data=resp_data)


@router.post("/sms/login", response_model=Response[LoginResponse], summary="短信验证码登录")
def sms_login(data: SmsLoginRequest, db: Session = Depends(get_db)):
    ok, msg = sms_service.verify_code(db, data.phone, data.code, "login")
    if not ok:
        raise HTTPException(status_code=401, detail=msg)

    user = db.query(User).filter(User.phone == data.phone, User.is_active == 1).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")

    user.last_login = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return Response(data=LoginResponse(
        access_token=token,
        user=UserOut.model_validate(user),
    ))


@router.post("/register", response_model=Response[LoginResponse], summary="手机号注册")
def register(data: UserRegisterRequest, db: Session = Depends(get_db)):
    ok, msg = sms_service.verify_code(db, data.phone, data.code, "register")
    if not ok:
        raise HTTPException(status_code=400, detail=msg)

    existing = db.query(User).filter(User.phone == data.phone).first()
    if existing:
        raise HTTPException(status_code=400, detail="该手机号已注册")

    user = User(
        phone=data.phone,
        username=data.phone,
        password=hash_password(data.password) if data.password else None,
        display_name=data.contact_name or data.company_name,
        company_name=data.company_name,
        contact_name=data.contact_name,
        business_type=data.business_type,
        target_regions=data.target_regions,
        last_login=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return Response(data=LoginResponse(
        access_token=token,
        user=UserOut.model_validate(user),
    ))


@router.post("/login", response_model=Response[LoginResponse], summary="密码登录")
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        (User.username == data.username) | (User.phone == data.username),
        User.is_active == 1,
    ).first()
    if not user or not user.password or not verify_password(data.password, user.password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    user.last_login = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return Response(data=LoginResponse(
        access_token=token,
        user=UserOut.model_validate(user),
    ))


@router.get("/me", response_model=Response[UserOut], summary="获取当前用户信息")
def get_me(current_user: User = Depends(get_current_user)):
    return Response(data=UserOut.model_validate(current_user))


@router.put("/me", response_model=Response[UserOut], summary="更新当前用户资料")
def update_me(
    data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return Response(data=UserOut.model_validate(current_user))
