"""

"""
import json
from app.util.chinac.chinac_open_api import ChinacOpenApi


def cloud_phone_get_phone_pageUrl(Id="cp-bn15bs1p5aglj39w"):
    """
        获取云手机直播链接
    """
    api = ChinacOpenApi()
    api.set_action('GetPhonePageUrl')
    api.set_http_method('POST')
    api.set_request_params({
        "Id": f"{Id}",
        'Region': 'cn-jsha-cloudphone-3',
        "IsShortUrl": True,
        "AllowGroupControl": True,
    })
    res = api.do()
    return json.loads(res['Info'])['data']['Url']


def cloud_phone_enable_image():
    """
    https://www.chinac.com/docs/api/anc/content/image/ListCloudPhoneEnableImage

    """
    api = ChinacOpenApi()
    api.set_action('ListCloudPhoneEnableImage')
    api.set_http_method('POST')
    api.set_request_params({
        'Region': 'cn-jsha-cloudphone-3',
    })
    res = api.do()
    print(json.dumps(json.loads(res['Info'])['data'], indent=2, ensure_ascii=False))
    return json.loads(res['Info'])


def cloud_phone_product_list():
    """
        https://www.chinac.com/docs/api/anc/content/base/ListCloudPhoneProduct
    """
    api = ChinacOpenApi()
    api.set_action('ListCloudPhoneProduct')
    api.set_http_method('POST')
    api.set_request_params({
        'Region': 'cn-jsha-cloudphone-3',
    })
    res = api.do()
    print(json.dumps(json.loads(res['Info'])['data'], indent=4, ensure_ascii=False))
    return json.loads(res['Info'])['data']

import logging

logger = logging.getLogger(__name__)

def cloud_phone_create():
    """
        创建云手机
        https://www.chinac.com/docs/api/anc/content/anc/OpenCloudPhone
        returl :
        {
            "data": {
                "ResourceIds": [
                    "cp-h815bs1q3bidh71z"
                ]
            }
        }
    """
    try:
        api = ChinacOpenApi()
        api.set_action('OpenCloudPhone')
        api.set_http_method('POST')
        api.set_request_params({
            'Region': 'cn-jsha-cloudphone-3',
            "CloudPhoneImageId": "i-aw15bs1n7bfyi63q", # 面具版本
            "PayType": "ONDEMAND",
            "ProductModelId": "805321" # 普通版
        })
        
        logger.info("Sending request to create cloud phone")
        res = api.do()
        logger.info(f"API response status: {res.get('Status')}")
        
        if res.get('Status') != 200:
            logger.error(f"API returned non-200 status: {res.get('Status')}")
            logger.error(f"API response info: {res.get('Info')}")
            return {'data': {}}
        
        info = json.loads(res['Info'])
        logger.info(f"Raw API response: {info}")
        
        # 处理API返回格式，确保返回的数据结构一致
        if 'data' in info:
            # 如果返回的是小写的data字段
            result = info
        elif 'Data' in info:
            # 如果返回的是大写的Data字段
            result = {'data': info['Data']}
        else:
            # 如果返回格式不符合预期
            result = {'data': {}}
        
        logger.info(f"Processed response: {result}")
        logger.info(f"Data to return: {result['data']}")
        return result
    except Exception as e:
        logger.error(f"Error creating cloud phone: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {'data': {}}

if __name__ == '__main__':
    # https://console.chinac.com/ci/1MdbACh8nW8
    # print(cloud_phone_get_phone_pageUrl())
    # 创建云手机
    cloud_phone_product_list()
    # cloud_phone_enable_image()
    # cloud_phone_create()
