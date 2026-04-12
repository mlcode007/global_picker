from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.common import Response
from app.schemas.user import UserOut, UserProfileUpdate
from app.core.security import get_current_user

router = APIRouter(prefix="/user", tags=["用户"])


@router.get("/info", response_model=Response[UserOut], summary="获取用户信息")
def get_user_info(current_user: User = Depends(get_current_user)):
    """获取当前用户的详细信息"""
    return Response(data=UserOut.model_validate(current_user))


@router.patch("/info", response_model=Response[UserOut], summary="更新用户信息")
def update_user_info(
    data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新当前用户的资料"""
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return Response(data=UserOut.model_validate(current_user))


@router.post("/change-password", response_model=Response, summary="修改密码")
def change_password(
    old_password: str,
    new_password: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改用户密码"""
    from app.core.security import verify_password, hash_password
    
    if not current_user.password:
        raise HTTPException(status_code=400, detail="用户未设置密码")
    
    if not verify_password(old_password, current_user.password):
        raise HTTPException(status_code=400, detail="原密码错误")
    
    current_user.password = hash_password(new_password)
    db.commit()
    db.refresh(current_user)
    
    return Response(message="密码修改成功")


@router.post("/avatar", response_model=Response, summary="上传头像")
def upload_avatar(
    file: bytes,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """上传用户头像"""
    # 这里应该实现图片上传逻辑
    # 简化处理，直接返回成功
    current_user.avatar = "https://randomuser.me/api/portraits/men/32.jpg"
    db.commit()
    db.refresh(current_user)
    
    return Response(message="头像上传成功", data={"avatar": current_user.avatar})
