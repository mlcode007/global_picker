import sys
sys.path.insert(0, '/Volumes/KIOXIA/SMZDM/MAC01/项目/我的项目/global_picker/backend')

from app.config import get_settings
from app.services.alipay_service import format_key

settings = get_settings()

print('App ID:', settings.ALIPAY_APP_ID)
print('Public key length:', len(settings.ALIPAY_PUBLIC_KEY))
print('Public key first 50 chars:', settings.ALIPAY_PUBLIC_KEY[:50])

formatted_public = format_key(settings.ALIPAY_PUBLIC_KEY, 'public')
print('Formatted public key first 100 chars:')
print(formatted_public[:100])
