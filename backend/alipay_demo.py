"""
支付宝支付简单Demo - 学习用

这个demo展示了支付宝PC扫码支付的核心流程：
1. 创建支付订单，生成二维码URL
2. 用户扫码支付
3. 接收支付宝异步通知，验证签名并处理支付结果

使用前准备：
1. 安装依赖: pip install python-alipay-sdk
2. 准备支付宝商户信息（APP_ID、私钥、公钥等）
3. 运行: python alipay_demo.py
"""

from alipay import AliPay
from alipay.utils import AliPayConfig
import os
import uuid
from datetime import datetime


# ==================== 配置信息 ====================
# 这些是你的支付宝商户信息，从支付宝开放平台获取
ALIPAY_CONFIG = {
    "app_id": "你的APP_ID",  # 支付宝开放平台创建的应用APPID
    "app_private_key": "你的应用私钥",  # RSA2私钥，用于签名请求
    "alipay_public_key": "支付宝公钥",  # 支付宝的公钥，用于验证回调签名
    "sandbox": True,  # True=沙箱环境测试，False=生产环境
}


class AlipayDemo:
    """支付宝支付Demo类"""
    
    def __init__(self):
        """初始化支付宝客户端"""
        self.app_id = ALIPAY_CONFIG["app_id"]
        self.sandbox = ALIPAY_CONFIG["sandbox"]
        
        # 根据环境设置网关地址
        if self.sandbox:
            # 沙箱环境网关
            self.gateway = "https://openapi-sandbox.dl.alipaydev.com/gateway.do"
        else:
            # 生产环境网关
            self.gateway = "https://openapi.alipay.com/gateway.do"
        
        # 创建AliPay实例
        self.alipay = AliPay(
            appid=self.app_id,
            app_notify_url=None,  # 默认回调地址，可在创建订单时指定
            app_private_key=ALIPAY_CONFIG["app_private_key"],
            alipay_public_key=ALIPAY_CONFIG["alipay_public_key"],
            sign_type="RSA2",  # 签名算法，固定RSA2
            debug=self.sandbox,  # debug模式
        )
        
        print(f"支付宝客户端初始化完成 [{'沙箱' if self.sandbox else '生产'}环境]")
    
    def create_qr_code_url(self, order_no: str, amount: str, subject: str) -> str:
        """
        创建扫码支付订单，返回二维码URL
        
        参数:
            order_no: 商户订单号（唯一）
            amount: 订单金额（元）
            subject: 订单标题
        
        返回:
            二维码URL，用户用支付宝APP扫码即可完成支付
        """
        # 构造订单参数
        order_string = self.alipay.api_alipay_trade_precreate(
            out_trade_no=order_no,  # 商户订单号
            total_amount=amount,    # 订单金额
            subject=subject,        # 订单标题
            notify_url="http://你的域名/api/v1/payment/alipay/notify",  # 异步通知地址
        )
        
        # 生成二维码URL
        qr_code_url = self.gateway + "?" + order_string
        
        return qr_code_url
    
    def verify_callback(self, data: dict, signature: str) -> bool:
        """
        验证支付宝异步回调签名
        
        参数:
            data: 回调数据（不包含sign字段）
            signature: 签名值
        
        返回:
            True=验证成功，False=验证失败
        """
        return self.alipay.verify(data, signature)


# ==================== 使用示例 ====================

def demo_create_payment():
    """演示创建支付订单"""
    print("\n===== 演示：创建支付订单 =====")
    
    # 初始化
    demo = AlipayDemo()
    
    # 生成订单号（实际项目中应该用数据库自增或雪花算法）
    order_no = f"DEMO{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6]}"
    
    # 创建订单
    amount = "0.01"  # 测试金额0.01元
    subject = "测试商品"
    
    qr_url = demo.create_qr_code_url(
        order_no=order_no,
        amount=amount,
        subject=subject
    )
    
    print(f"订单号: {order_no}")
    print(f"金额: {amount}元")
    print(f"标题: {subject}")
    print(f"二维码URL: {qr_url}")
    print("\n提示：将此URL生成二维码，用支付宝APP扫码即可支付（沙箱环境需用沙箱APP）")
    
    return order_no


def demo_verify_callback():
    """演示验证支付回调"""
    print("\n===== 演示：验证支付回调 =====")
    
    demo = AlipayDemo()
    
    # 模拟支付宝异步通知数据
    # 实际项目中，这些数据来自支付宝POST请求
    mock_callback_data = {
        "gmt_create": "2024-01-01 12:00:00",
        "charset": "utf-8",
        "seller_email": "xxx@alipay.com",
        "subject": "测试商品",
        "sign": "模拟签名值",
        "buyer_id": "2088xxx",
        "body": "",
        "invoice_amount": "0.01",
        "notify_id": "xxx",
        "fund_bill_list": "[{\"amount\":\"0.01\",\"fundChannel\":\"ALIPAYACCOUNT\"}]",
        "notify_type": "trade_status_sync",
        "trade_status": "TRADE_SUCCESS",  # 支付成功状态
        "receipt_amount": "0.01",
        "app_id": "你的APP_ID",
        "buyer_pay_amount": "0.01",
        "sign_type": "RSA2",
        "seller_id": "2088xxx",
        "gmt_payment": "2024-01-01 12:00:01",
        "notify_time": "2024-01-01 12:00:02",
        "version": "1.0",
        "out_trade_no": "DEMO20240101120000abcdef",
        "total_amount": "0.01",
        "trade_no": "2024010122001xxx",
        "auth_app_id": "你的APP_ID",
        "buyer_logon_id": "xxx@alipay.com",
        "point_amount": "0.00",
    }
    
    signature = mock_callback_data.pop("sign")
    
    # 验证签名
    is_valid = demo.verify_callback(mock_callback_data, signature)
    
    if is_valid:
        trade_status = mock_callback_data.get("trade_status")
        order_no = mock_callback_data.get("out_trade_no")
        
        print(f"签名验证成功!")
        print(f"订单号: {order_no}")
        print(f"支付状态: {trade_status}")
        
        if trade_status == "TRADE_SUCCESS" or trade_status == "TRADE_FINISHED":
            print("支付成功！可以更新订单状态了")
        else:
            print(f"支付未完成，状态: {trade_status}")
    else:
        print("签名验证失败！可能是伪造的回调")


# ==================== 关键概念说明 ====================

def print_concepts():
    """打印关键概念说明"""
    print("""
===== 支付宝支付核心概念 =====

1. 订单号 (out_trade_no)
   - 商户系统生成的唯一订单号
   - 建议使用：时间戳 + 随机数 或 雪花算法
   - 长度不超过64字符

2. 签名机制
   - 请求签名：用你的私钥对请求参数签名，支付宝用你的公钥验证
   - 回调验证：支付宝用它的私钥对回调数据签名，你用支付宝公钥验证
   - 确保数据不被篡改

3. 支付状态 (trade_status)
   - WAIT_BUYER_PAY: 交易创建，等待买家付款
   - TRADE_CLOSED: 交易关闭（超时或取消）
   - TRADE_SUCCESS: 支付成功
   - TRADE_FINISHED: 交易完成（过了退款期）

4. 异步通知 (notify_url)
   - 支付完成后，支付宝会POST通知到这个URL
   - 必须返回 "success" 字符串，否则支付宝会重复通知
   - 通知可能重复，需要处理幂等性

5. 沙箱环境
   - 用于测试，不产生真实交易
   - 需要用沙箱版支付宝APP扫码
   - 网关地址与生产环境不同

6. 安全要点
   - 私钥绝对不能泄露
   - 回调必须验证签名
   - 金额要以支付宝回调为准，不能信任前端
   - 处理通知时要检查订单金额是否匹配
""")


if __name__ == "__main__":
    print("支付宝支付Demo - 学习版")
    print("=" * 50)
    
    # 打印概念说明
    print_concepts()
    
    # 演示创建支付（需要配置真实的密钥才能运行）
    # demo_create_payment()
    
    # 演示验证回调
    # demo_verify_callback()
    
    print("\n提示：配置好密钥后，取消注释上面的demo函数即可运行")
