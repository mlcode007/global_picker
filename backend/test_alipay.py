import sys
sys.path.insert(0, '/Volumes/KIOXIA/SMZDM/MAC01/项目/我的项目/global_picker/backend')

from app.config import get_settings
from app.services.alipay_service import format_key

settings = get_settings()

print('App ID:', settings.ALIPAY_APP_ID)
print('Private key length:', len(settings.ALIPAY_PRIVATE_KEY))

private_key = format_key(settings.ALIPAY_PRIVATE_KEY, 'private')
print('Formatted private key first 100 chars:')
print(private_key[:100])

try:
    from alipay import AliPay
    alipay = AliPay(
        appid=settings.ALIPAY_APP_ID,
        app_notify_url='http://test.com/notify',
        app_private_key_string=private_key,
        alipay_public_key_string=format_key(settings.ALIPAY_PUBLIC_KEY, 'public'),
        sign_type='RSA2',
        debug=True
    )
    print('SUCCESS: AliPay initialized')
except Exception as e:
    print(f'FAILED: {e}')
    import traceback
    traceback.print_exc()
