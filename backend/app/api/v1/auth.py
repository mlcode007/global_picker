from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.common import Response
from app.schemas.user import UserLogin, TokenOut, UserOut
from app.core.security import verify_password, create_access_token, hash_password

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", response_model=Response[TokenOut], summary="用户登录")
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username, User.is_active == 1).first()
    if not user or not verify_password(data.password, user.password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    user.last_login = datetime.now(timezone.utc)
    db.commit()
    token = create_access_token({"sub": str(user.id)})
    return Response(data=TokenOut(access_token=token))


@router.post("/register", response_model=Response[UserOut], summary="注册用户（仅开发环境）")
def register(data: UserLogin, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = User(
        username=data.username,
        password=hash_password(data.password),
        display_name=data.username,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return Response(data=UserOut.model_validate(user))
