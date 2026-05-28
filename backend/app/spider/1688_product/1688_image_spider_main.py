import requests

cookies = {
    'lid': 'bruce_1905',
    'cookie2': '16d4316d670a90a301d9aa110edefd23',
    't': '4cc6746a3701973a32512e0631e2eda0',
    '_tb_token_': '7a7e7e1483eef',
    'leftMenuLastMode': 'COLLAPSE',
    'leftMenuModeTip': 'shown',
    'xlly_s': '1',
    'plugin_home_downLoad_cookie': '%E4%B8%8B%E8%BD%BD%E6%8F%92%E4%BB%B6',
    'sgcookie': 'E1004zJtTNJ73%2F6ntTzm8mxCx5dDTMKDkC35kUqC%2B8Kk0lFToSrdkbnKJb6UrAzd7P2P9ZpcQ7p2gzP7dvzL%2BKwEIZeIA%2FUuh1B6hk9XMzcJFHdO%2BTgh7UTnoPL%2FPRoKyviQ',
    'uc4': 'nk4=0%40A7sK0ENOghHbY9cyprQudklvQNV0&id4=0%40Vh%2B9OVk4A%2Baa07S8IdZk2b7p82M%3D',
    '__last_loginid__': 'b2b-777329507',
    '__last_memberid__': 'b2b-777329507',
    'x-hng': 'lang=zh-CN&domain=h5api.m.1688.com',
    'trackId': '8728253e25bf4868ada49f281865852b',
    'mtop_partitioned_detect': '1',
    '_m_h5_tk': '3321cdbf886ff9cb75571bf845224a0c_1778960013040',
    '_m_h5_tk_enc': '9823943c17b15a0c688775949899e90f',
    'union': '{"amug_biz":"oneself","amug_fl_src":"awakeId_984","creative_url":"https%3A%2F%2Fair.1688.com%2Fkapp%2FinnovateHub%2Fextension-offer-search%2FimageSearch%3Famug_biz%3Doneself%26amug_fl_src%3DawakeId_984%26language%3Dzh-CN%26env%3Dtest%26messageChannelId%3Dplugin-infra-suite-1ipz1mgla5b-1%26extensionVersion%3D1.1.1%26enableIframeAppRenderCloseBtn%3Dtrue","creative_time":1778953078309}',
    '_user_vitals_session_data_': '{"user_line_track":true,"ul_session_id":"psv76btiahe","last_page_id":"www.1688.com%2Fo6529q1dnnm"}',
    '_samesite_flag_': 'true',
    'tracknick': '',
    '__cn_logon__': 'false',
    'cna': 'GKVzIgiRj0UCAW/KzDKBgp+I',
    'x5sectag': '334871',
    'x5sec': '7b22733b32223a2234393865373761363138303137376461222c22617365727665723b33223a22307c434e50616f744147454b2b6b75644d45476773334e7a637a4d6a6b314d4463374e43494b59324677633278705a4756324d6a4371787371702f502f2f2f2f3842227d',
    'tfstk': 'g6exzWAaLgKvmfW5JKfusYOgHPIu5_q44rrBIV0D1zU8Srni1ji6V3g87qcmhrDTfluzmfqinCMTYyUwi1kXBhZUJfv0ixVTeza3sScgcV9TSl20SxN0BAH4ESvioZkTfyDO-wXhKorq3A_h-QH052kqjFtjlFmSPcHtcQ9kN0qqQA_kqd1hpozxhb_icci52cmZfEascuTSj4i6GAasPbiIxEMsCPs-PDiH1Ig6C0TSX4gsCAasFQgrXAib5As8V4os1qjxztieB7rWl5g57KfO68nxMVpmydhaKpDmRDuJCLM-DzuQc4p6C2oOcDZ_5NpidWz8BXahBLk0v7MSD7I6NqGLGrmzW9pjl8Ebhq2frK0b3uN3Izs6CVF7OXFQcaA-27Z0eb2CJdh4NrPE6RblLxV3xRlQhtLErXoTJxNRPKUC4ge3poZW-2nMMgIJ_Clj4ak7xgjcl_Nx22jjGCRZ98o--gBM_Cljm03hcHdw_XGc.',
    'isg': 'BEhICwX8tmOTxdk3LDlBM5qTGbBa8az7HH9LtwL8RkPh3ftHqgoxim4TVb2tIWTT',
}

headers = {
    'accept': '*/*',
    'accept-language': 'zh,zh-CN;q=0.9',
    'cache-control': 'no-cache',
    'origin': 'https://air.1688.com',
    'pragma': 'no-cache',
    'priority': 'u=1, i',
    'referer': 'https://air.1688.com/kapp/innovateHub/extension-offer-search/imageSearch/offer-viewer-market',
    'sec-ch-ua': '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-site',
    'sec-fetch-storage-access': 'active',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
    'x-1688extension-secret': 'tMrw7DZ7MZzkt0fGiWrinjC0W8MI3SnJ6qf58CwcbUXnneJ3gEKUVYNzkuPuMMBfIGe/aJ5D2vuRaX+ukJW+UeVsmDSDL8u8inB/mdPCCUnM7Ij+j5KswHXiQK2W4t9j4oWlqE5sYVvLBHSjLtrBFZ+JynVlSyHnz5y8D/dXLAX5LpqQ/Vf+s4BxjIJFY5g+JjTgA+JizaD4Lxst5xzZkVfdnCraVVDLx7BifT9gUDOQCLzULa3psCWFvBqXxP62wTezrRUFt9Jh/qTusH5EXJ0lua8=',
    'x-accept-language': 'zh-CN',
}

params = {
    'jsv': '2.7.2',
    'appKey': '12574478',
    't': '1778953145446',
    'sign': '67d851c50607aa0d389fd3b712cd5ac7',
    'dataType': 'json',
    'api': 'mtop.1688.pc.plugin.imageSearch.plugin.search',
    'v': '1.1',
    'type': 'originaljson',
    'data': '{"params":"{\\"searchScene\\":\\"imageEx\\",\\"serviceGroupName\\":\\"service.group.pc.image\\",\\"interfaceName\\":\\"imageExtraSearchService\\",\\"serviceParam.extendParam[subChannel]\\":\\"pc_image_plugin\\",\\"serviceParam.extendParam[imageId]\\":\\"1345108748288455835\\",\\"serviceParam.extendParam[appName]\\":\\"imageExtra\\",\\"abRequest.level3Biz\\":\\"main\\",\\"abRequest.level2Biz\\":\\"image\\",\\"abRequest.level1Biz\\":\\"search\\",\\"serviceParam.extendParam[pageSize]\\":10,\\"serviceParam.extendParam[beginPage]\\":1,\\"serviceParam.extendParam[tags]\\":\\"\\",\\"serviceParam.extendParam[offerTags]\\":\\"\\",\\"serviceParam.extendParam[province]\\":\\"\\",\\"serviceParam.extendParam[city]\\":\\"\\",\\"serviceParam.extendParam[quantityBegin]\\":0,\\"serviceParam.extendParam[sortField]\\":\\"\\"}","scene":"IMAGE_SEARCH_DRAWER"}',
}

response = requests.get(
    'https://h5api.m.1688.com/h5/mtop.1688.pc.plugin.imagesearch.plugin.search/1.1/',
    params=params,
    cookies=cookies,
    headers=headers,
)
print(response.json())