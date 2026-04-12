import logging
from sqlalchemy.orm import Session
from app.models.points import UserPoints, PointsTransaction

logger = logging.getLogger(__name__)


class PointsManager:
    """积分管理器 - 负责用户积分的管理"""

    def __init__(self, db: Session):
        self.db = db

    def get_user_points(self, user_id: int) -> UserPoints:
        """获取用户积分信息"""
        user_points = self.db.query(UserPoints).filter(UserPoints.user_id == user_id).first()
        
        if not user_points:
            # 如果用户没有积分记录，创建一个
            user_points = UserPoints(user_id=user_id)
            self.db.add(user_points)
            self.db.commit()
            self.db.refresh(user_points)
        
        return user_points

    def add_points(self, user_id: int, amount: int, reason: str, related_id: str = None) -> bool:
        """为用户添加积分"""
        if amount <= 0:
            logger.warning("Invalid points amount: %d", amount)
            return False
        
        user_points = self.get_user_points(user_id)
        
        # 更新积分
        user_points.points += amount
        user_points.total_earned += amount
        
        # 记录交易
        transaction = PointsTransaction(
            user_id=user_id,
            type="earn",
            amount=amount,
            reason=reason,
            related_id=related_id
        )
        self.db.add(transaction)
        self.db.commit()
        
        logger.info("Added %d points to user %d: %s", amount, user_id, reason)
        return True

    def deduct_points(self, user_id: int, amount: int, reason: str, related_id: str = None) -> bool:
        """扣除用户积分"""
        if amount <= 0:
            logger.warning("Invalid points amount: %d", amount)
            return False
        
        user_points = self.get_user_points(user_id)
        
        if user_points.points < amount:
            logger.warning("User %d has insufficient points: %d < %d", user_id, user_points.points, amount)
            return False
        
        # 更新积分
        user_points.points -= amount
        user_points.total_consumed += amount
        
        # 记录交易
        transaction = PointsTransaction(
            user_id=user_id,
            type="consume",
            amount=amount,
            reason=reason,
            related_id=related_id
        )
        self.db.add(transaction)
        self.db.commit()
        
        logger.info("Deducted %d points from user %d: %s", amount, user_id, reason)
        return True

    def check_points(self, user_id: int, amount: int) -> bool:
        """检查用户积分是否足够"""
        user_points = self.get_user_points(user_id)
        return user_points.points >= amount

    def get_transactions(self, user_id: int, limit: int = 20, offset: int = 0) -> list:
        """获取用户积分交易记录"""
        transactions = self.db.query(PointsTransaction).filter(
            PointsTransaction.user_id == user_id
        ).order_by(
            PointsTransaction.created_at.desc()
        ).limit(limit).offset(offset).all()
        
        return transactions

    def get_user_phone_limit(self, user_id: int) -> int:
        """获取用户云手机数量限制"""
        # 默认限制为1台
        return 1