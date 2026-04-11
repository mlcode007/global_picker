"""
openapi接口
执行完do后会重置参数
不会重置设置的accessKeyId、accessKeySecret、openApiUrl
"""
import base64
import hashlib
import hmac
import json
import time
import urllib.parse
import urllib.request


class ChinacOpenApi:
    """
        初始化
    """
    def __init__(self, access_key_id='875dbd8f3ba649e79959d8a540f05f0b', access_key_secret='ac24b38883ca4335aceeb56a9d29e8ce'):
        super(ChinacOpenApi, self).__init__()
        # 用户Access Key，可以通过用控新增、查看
        self._access_key_id = access_key_id

        # 用户Access Key Secret，可以通过用控新增、查看
        self._access_key_secret = access_key_secret

        # openapi通信地址地址，默认线上v2版，可以通过setOpenApiUrl修改
        # 结尾不含/
        self.open_api_url = 'https://api.chinac.com/v2'

        # 处理后的openapi通信地址
        self.request_url = ''

        # 请求方式，默认GET，可以通过setHttpMethod修改
        # 支持的有GET、POST、PUT等
        self.http_method = 'GET'

        # 请求操作Action名称，如DescribeInstances
        self.action = ''

        # 请求参数数组，键值对应请求参数名称和值，如：
        # {'Region': 'a', 'ProductStatus': 'NORMAL'}
        self.params = None

        # json参数，一般用于POST、PUT
        self.json_body = None

        # 请求头数组
        self.headers = {}

    # 修改openapi默认通信地址
    def set_open_api_url(self, open_api_url):
        self.open_api_url = open_api_url

    # 修改修改请求方式
    def set_http_method(self, http_method):
        self.http_method = http_method

    # 设置操作方法Action
    def set_action(self, action):
        self.action = action

    # 设置请求参数
    def set_request_params(self, params):
        self.params = params

    # 请求并返回结果
    def do(self):
        self.generate_headers()
        self.dealParams()
        res = self.request()
        self.refresh()
        return res

    # 生成请求头
    def generate_headers(self):
        self.headers = {
            'Content-Type': 'application/json;charset=UTF-8',
            'Accept-Encoding': '*',
            'Date': time.strftime("%Y-%m-%dT%H:%M:%S +0800", time.localtime())
        }

    # 处理参数，生成通信签名等
    def dealParams(self):
        yparams = {
            'Action': self.action,
            'Version': '1.0', #目前固定1.0
            'AccessKeyId': self._access_key_id,
            'Date': self.headers['Date']
        };
        params = yparams.copy()
        if self.params:
            if self.http_method == 'GET':
                params.update(self.params)
            else:
                self.json_body = json.dumps(self.params).encode(encoding='UTF8')
        # 生成签名，更新url
        res = self.generate_signature(params)
        self.request_url = self.open_api_url + '?' + res['query'] + '&Signature=' + res['signature']

    # 生成签名
    def generate_signature(self, params):
        sign_string = [self.http_method, "\n"]
        query = self.percent_urlencode_params(params)
        # md5加密参数
        m = hashlib.md5()
        m.update(bytearray(query, 'utf-8'))
        sign_string.append(m.hexdigest())
        sign_string.append("\n")
        sign_string.append(self.headers['Content-Type'])
        sign_string.append("\n")
        sign_string.append(self.percent_urlencode_str(self.headers['Date']))
        sign_string.append("\n")
        sign_string = ''.join(sign_string)
        signature = self.percent_urlencode_str(self.sha_hmac256_signature(sign_string))
        return {'query': query, 'signature': signature}

    # encodeurl参数
    def percent_urlencode_params(self, params):
        urlstr = urllib.parse.urlencode(params)
        return self.percent_encode(urlstr)

    # encodeurl字符串
    def percent_urlencode_str(self, urlstr):
        urlstr = urllib.parse.quote(urlstr)
        return self.percent_encode(urlstr)

    # 转成url通信标准RFC 3986
    def percent_encode(self, urlstr):
        urlstr = urlstr.replace('+', '%20')
        urlstr = urlstr.replace('*', '%2A')
        urlstr = urlstr.replace('%7E', '~')
        return urlstr

    # base64 hmac256加密
    def sha_hmac256_signature(self, sign_string):
        h = hmac.new(bytearray(self._access_key_secret, 'utf-8'), bytearray(sign_string, 'utf-8'), hashlib.sha256)
        signature = str(base64.encodebytes(h.digest()).strip(), 'utf-8')
        return signature

    # 请求通信
    def request(self):
        import ssl
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(
            self.request_url,
            data=self.json_body,
            headers=self.headers,
            method=self.http_method
        )
        res = urllib.request.urlopen(req, context=context)
        return {'Status': res.getcode(), 'Info': res.read().decode('utf-8')}

    # 请求后重置参数
    def refresh(self):
        self.request_url = ''
        self.http_method = 'GET'
        self.action = '';
        self.params = None
        self.json_body = None
        self.headers = {}

    # ── 云手机相关扩展方法 ──────────────────────────────────────

    def do_cloud_phone_create(self, params: dict) -> dict:
        """
        创建云手机（Chinac API 扩展方法）
        
        参数示例：
        {
            "InstanceType": "ci.g5.large",
            "ImageId": "img-cloudphone-xxx",
            "Region": "cn-jsha-cloudphone-3",
            "PhoneName": "auto-scale-xxx"
        }
        
        返回示例：
        {
            "ResourceIds": [
                "cp-h815bs1q3bidh71z"
            ]
        }
        """
        # 安全检查：限制创建参数
        if not params.get('InstanceType'):
            raise ValueError('InstanceType is required')
        if not params.get('ImageId'):
            raise ValueError('ImageId is required')
        if not params.get('Region'):
            raise ValueError('Region is required')
        
        self.set_action('OpenCloudPhone')
        self.set_http_method('POST')
        self.set_request_params(params)
        res = self.do()
        
        try:
            data = json.loads(res['Info'])
            result = data.get('Data', data)
            
            # 处理新的返回格式
            if 'ResourceIds' in result and isinstance(result['ResourceIds'], list) and len(result['ResourceIds']) > 0:
                # 转换为统一格式
                return {
                    'Id': result['ResourceIds'][0],
                    'Status': 'CREATING'
                }
            return result
        except Exception as e:
            print(f"Error parsing cloud phone create response: {e}")
            return res

    def do_describe_cloud_phones(self, phone_ids: list = None, status: str = None) -> dict:
        """
        查询云手机列表（Chinac API 扩展方法）
        
        参数示例：
        {
            "Region": "cn-jsha-cloudphone-3",
            "Ids": ["cp-bn15bs1p5aglj39w"],
            "Status": "RUNNING"
        }
        
        返回示例：
        {
            "CloudPhoneSet": [
                {
                    "Id": "cp-bn15bs1p5aglj39w",
                    "Status": "RUNNING",
                    "PhoneName": "xxx",
                    "InstanceType": "ci.g5.large"
                }
            ]
        }
        """
        self.set_action('DescribeCloudPhones')
        self.set_http_method('GET')
        
        params = {"Region": "cn-jsha-cloudphone-3"}
        if phone_ids:
            params["Ids"] = phone_ids
        if status:
            params["Status"] = status
            
        self.set_request_params(params)
        res = self.do()
        
        try:
            data = json.loads(res['Info'])
            return data.get('Data', data)
        except:
            return res

    def do_start_cloud_phone(self, phone_id: str) -> dict:
        """启动云手机"""
        self.set_action('StartCloudPhone')
        self.set_http_method('POST')
        self.set_request_params({
            "Id": phone_id,
            "Region": "cn-jsha-cloudphone-3"
        })
        res = self.do()
        
        try:
            data = json.loads(res['Info'])
            return data.get('Data', data)
        except:
            return res

    def do_stop_cloud_phone(self, phone_id: str) -> dict:
        """停止云手机"""
        self.set_action('StopCloudPhone')
        self.set_http_method('POST')
        self.set_request_params({
            "Id": phone_id,
            "Region": "cn-jsha-cloudphone-3"
        })
        res = self.do()
        
        try:
            data = json.loads(res['Info'])
            return data.get('Data', data)
        except:
            return res

    def do_delete_cloud_phone(self, phone_id: str) -> dict:
        """删除云手机"""
        self.set_action('DeleteCloudPhone')
        self.set_http_method('POST')
        self.set_request_params({
            "Id": phone_id,
            "Region": "cn-jsha-cloudphone-3"
        })
        res = self.do()
        
        try:
            data = json.loads(res['Info'])
            return data.get('Data', data)
        except:
            return res
