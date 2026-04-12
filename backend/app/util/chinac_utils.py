"""

"""
import json
import logging
import requests
logger = logging.getLogger(__name__)
try:
    from app.util.chinac.chinac_open_api import ChinacOpenApi
except Exception as e:
    from chinac.chinac_open_api import ChinacOpenApi

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
        "IsShortUrl": False,
        "AllowGroupControl": True,
    })
    res = api.do()
    return json.loads(res['Info'])['data']['Url']


"""
    创建云手机
"""

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
            "CloudPhoneImageId": "i-6215bs1q3cesf42x", # 自定义拼多多镜像
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

"""
    验证云手机
"""

def cloud_phone_describe_phone(id):
    """
    https://www.chinac.com/docs/api/anc/content/anc/DescribeCloudPhone
    return:
        不存在的话:
        {
          "Code": "CloudPhoneNotFound",
          "ErrorCode": "3200",
          "ErrorMessage": "云手机不存在",
          "ResponseCode": 170002,
          "ResponseDate": "2026-04-11T16:37:22.005+00:00",
          "ResponseMsg": "资源不存在"
        }
        存在的话:
        {
          "BasicInfo": {
            "AdbStatus": "CLOSE",
            "CreateTime": 1775922071000,
            "Eip": "103.36.206.192",
            "GroupId": "cpg-c111fa572def4bc1b2113d87a706671f",
            "GroupName": "默认分组",
            "HostName": "jsha3-zun-arm11",
            "Id": "cp-jx15bs1q3bn5b31u",
            "ImageId": "i-aw15bs1n7bfyi63q",
            "ImageName": "Android 11 Magisk版",
            "IntranetIp": "10.20.17.149",
            "IsEnable": 1,
            "LastStartTime": 1775922079000,
            "Name": "A2604110010",
            "NetworkType": "COMMON",
            "PayType": "ONDEMAND",
            "ProductModelId": 805321,
            "ProductModelName": "普通版",
            "ProductStatus": "NORMAL",
            "ProductType": "普通版",
            "Region": "cn-jsha-cloudphone-3",
            "RegionId": 208,
            "RegionName": "江苏三区",
            "Status": "START",
            "TaskStatus": "NONE",
            "TemplateId": "cpit-u215bs1q2qgj3652",
            "TemplateName": "2026-03-18-02 版",
            "UpdateTime": 1775922081000
          },
          "BillInfo": {
            "CreateTime": 1775922071000,
            "PayType": "ONDEMAND",
            "ProductStatus": "NORMAL"
          },
          "Flavor": {
            "Cpu": 4,
            "DisplaySize": "720*1280",
            "Dpi": 320,
            "FlavorId": "cpf-lg15bs1q3bn5b48e",
            "FlavorName": "普通版",
            "Os": "Android 11 Magisk版",
            "Ram": 3,
            "Storage": 32
          },
          "NetInfo": {
            "CloudPhoneNetworkType": "COMMON",
            "Id": "cpn-1z15bmb3f03546",
            "InnerIp": "10.20.17.149",
            "OuterIp": "103.36.206.192",
            "ProductStatus": "NORMAL",
            "RouterId": "r-ne15bmb3f0423m",
            "SubnetId": "s-kw15bmb3f0b84h"
          }
        }

    """
    api = ChinacOpenApi()
    api.set_action('DescribeCloudPhone')
    api.set_http_method('POST')
    api.set_request_params({
        'Region': 'cn-jsha-cloudphone-3',
        'Id': f'{id}'
    })
    res = api.do()
    print(json.dumps(json.loads(res['Info'])['data'], indent=2, ensure_ascii=False))
    return json.loads(res['Info'])

def get_current_id():
    return requests.get('https://httpbin.org/ip').json()['origin']

def cloud_phone_create_adb(id):
    """
        https://www.chinac.com/docs/api/anc/content/operate/CreateCloudPhoneAdb

    """

    api = ChinacOpenApi()
    api.set_action('CreateCloudPhoneAdb')
    api.set_http_method('POST')
    api.set_request_params({
        'Region': 'cn-jsha-cloudphone-3',
        'CloudPhoneIds': [f'{id}'],
        'Ips': [get_current_id()]
    })
    res = api.do()
    print(json.dumps(json.loads(res['Info'])['data'], indent=2, ensure_ascii=False))
    return json.loads(res['Info'])

def cloud_phone_check_status(id):
    """
    检查云手机状态
    
    Args:
        id: 云手机设备ID
        
    Returns:
        dict: 包含code和message的字典
            code: 状态码，0表示成功，-1表示设备不存在，-2表示ADB连接失败，-3表示ADB连接超时
            message: 状态描述
    """
    try:
        device_info = cloud_phone_describe_phone(id)
        # 检查返回格式
        if 'data' not in device_info:
            return {
                "code" : -1,
                "message": "设备不存在或返回格式错误"
            }
        
        basic_info = device_info['data'].get("BasicInfo", {})
        adb_host_port = basic_info.get('AdbHostPort')
        adb_status = basic_info.get('AdbStatus')
        
        # 检查AdbStatus是否为CLOSE，如果是则开启ADB
        if adb_status == 'CLOSE':
            print("设备ADB状态为CLOSE，尝试开启ADB")
            cloud_phone_create_adb(id)
            # 重新获取设备信息
            device_info = cloud_phone_describe_phone(id)
            basic_info = device_info['data'].get("BasicInfo", {})
            adb_host_port = basic_info.get('AdbHostPort')
        
        if not adb_host_port:
            print("设备未开启ADB权限")
            return {
                "code" : -4,
                "message": "设备未开启ADB权限"
            }
        
        print(f"设备ADB端口: {adb_host_port}")
    except Exception as e:
        print(f"获取设备信息失败: {e}")
        return {
            "code" : -1,
            "message": "设备不存在或获取信息失败"
        }
    
    # 验证adb是否成功
    import subprocess
    try:
        result = subprocess.run(['adb', 'connect', adb_host_port], capture_output=True, text=True, timeout=3)
        if result.returncode == 0 and 'connected' in result.stdout:
            print("ADB连接成功")
            return {
                "code" : 0,
                "message": "ADB连接成功"
            }
        else:
            print(f"ADB连接失败: {result.stderr}")
            return {
                "code" : -2,
                "message": "ADB连接失败"
            }
    except subprocess.TimeoutExpired:
        print("ADB连接超时")
        cloud_phone_create_adb(id)
        return {
            "code" : -3,
            "message": "ADB连接超时"
        }
    except Exception as e:
        print(f"ADB连接异常: {e}")
        return {
            "code" : -5,
            "message": "ADB连接异常"
        }




if __name__ == '__main__':
    # https://console.chinac.com/ci/1MdbACh8nW8
    # print(cloud_phone_get_phone_pageUrl())
    # 创建云手机
    # cloud_phone_product_list()
    # cloud_phone_enable_image()
    cloud_phone_create()
    # 检查云手机状态
    # 1. 通过id检查云手机是否存在 如果不存在则更新状态
    # 2. 开通云手机adb权限
    # 3. 链接adb 如果链接不上,则更新状态
    # cloud_phone_describe_phone(id="cp-qd15bs1q3c67i19h")
    # cloud_phone_create_adb(id="cp-qd15bs1q3c67i19h")
    # print(cloud_phone_check_status(id='cp-jx15bs1q3bn5b31u'))
