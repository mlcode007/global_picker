from alipay import AliPay
from app.config import get_settings
import ssl
import urllib.request
import json


def format_key(key: str, key_type: str) -> str:
    key = key.strip()
    if key_type == 'private':
        if not key.startswith('-----BEGIN'):
            key = '-----BEGIN RSA PRIVATE KEY-----\n' + key + '\n-----END RSA PRIVATE KEY-----'
    elif key_type == 'public':
        if not key.startswith('-----BEGIN'):
            key = '-----BEGIN PUBLIC KEY-----\n' + key + '\n-----END PUBLIC KEY-----'
    return key


ssl._create_default_https_context = ssl._create_unverified_context


class AlipayService:
    def __init__(self):
        settings = get_settings()
        self.app_id = settings.ALIPAY_APP_ID
        self.sandbox = settings.ALIPAY_SANDBOX
        self.notify_url = settings.ALIPAY_NOTIFY_URL

        if self.sandbox:
            self.gateway = "https://openapi-sandbox.dl.alipaydev.com/gateway.do"
        else:
            self.gateway = "https://openapi.alipay.com/gateway.do"

        private_key = format_key(settings.ALIPAY_PRIVATE_KEY, 'private')
        public_key = format_key(settings.ALIPAY_PUBLIC_KEY, 'public')

        self.alipay = AliPay(
            appid=self.app_id,
            app_notify_url=self.notify_url,
            app_private_key_string=private_key,
            alipay_public_key_string=public_key,
            sign_type="RSA2",
            debug=self.sandbox,
        )

    def create_qr_code_url(self, out_trade_no: str, total_amount: str, subject: str) -> str:
        biz_content = {
            "out_trade_no": out_trade_no,
            "total_amount": total_amount,
            "subject": subject,
        }
        
        try:
            signed_string = self.alipay.client_api(
                "alipay.trade.precreate",
                biz_content=biz_content,
                notify_url=self.notify_url,
            )
            
            url = self.gateway + "?" + signed_string
            response = urllib.request.urlopen(url, timeout=10).read().decode()
            result = json.loads(response)
            
            if "error_response" in result:
                error = result["error_response"]
                raise Exception(f"支付宝API错误: {error.get('sub_msg', error.get('msg', '未知错误'))}")
            
            alipay_response = result.get("alipay_trade_precreate_response", {})
            if alipay_response.get("code") != "10000":
                raise Exception(f"支付宝业务错误: {alipay_response.get('sub_msg', alipay_response.get('msg', '未知错误'))}")
            
            qr_code = alipay_response.get("qr_code")
            if not qr_code:
                raise Exception("未返回二维码")
            
            return qr_code
        except Exception as e:
            print(f"Alipay API error: {e}")
            raise

    def verify_callback(self, data: dict, signature: str) -> bool:
        return self.alipay.verify(data, signature)

    def query_order(self, out_trade_no: str) -> dict:
        biz_content = {
            "out_trade_no": out_trade_no,
        }
        
        try:
            signed_string = self.alipay.client_api(
                "alipay.trade.query",
                biz_content=biz_content,
            )
            
            url = self.gateway + "?" + signed_string
            response = urllib.request.urlopen(url, timeout=10).read().decode()
            result = json.loads(response)
            
            if "error_response" in result:
                error = result["error_response"]
                raise Exception(f"支付宝API错误: {error.get('sub_msg', error.get('msg', '未知错误'))}")
            
            alipay_response = result.get("alipay_trade_query_response", {})
            if alipay_response.get("code") != "10000":
                raise Exception(f"支付宝业务错误: {alipay_response.get('sub_msg', alipay_response.get('msg', '未知错误'))}")
            
            return alipay_response
        except Exception as e:
            print(f"Alipay query error: {e}")
            raise
