import requests

def batch1():
    headers = {
        'accept': '*/*',
        'accept-language': 'zh-CN,zh;q=0.9,vi;q=0.8',
        'content-type': 'application/json',
        'origin': 'https://shop.tiktok.com',
        'priority': 'u=1, i',
        'referer': 'https://shop.tiktok.com/',
        'sec-ch-ua': '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'cross-site',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
    }

    params = {
        'biz_id': 'oec_bssdk',
    }

    json_data = {
        'ev_type': 'batch',
        'list': [
            {
                'ev_type': 'custom',
                'payload': {
                    'name': 'bssdk_unisec_core_gen_core_signature',
                    'type': 'event',
                    'categories': {
                        'appid': '1988',
                    },
                },
                'common': {
                    'bid': 'oec_bssdk',
                    'pid': 'https://shop.tiktok.com/view/product/1733957732396402462',
                    'view_id': 'https://shop.tiktok.com/view/product/1733957732396402462_1778875880682',
                    'user_id': '4f76b5ce-cbfc-4f2f-a3b8-b8ce0b19f31c',
                    'device_id': '9ff9d288-42c4-474d-b607-eec2256933df',
                    'session_id': 'ac8bcd41-ba9c-4d9a-ad32-bb30a06a6667',
                    'release': '',
                    'env': 'production',
                    'url': 'https://shop.tiktok.com/view/product/1733957732396402462?region=TH&locale=zh-CN',
                    'timestamp': 1778875894603,
                    'sdk_version': '1.12.1',
                    'sdk_name': 'SDK_SLARDAR_WEB',
                    'context': {},
                    'network_type': '3g',
                },
            },
            {
                'ev_type': 'custom',
                'payload': {
                    'name': 'bssdk_unisec_core_gen_core_signature_duration',
                    'type': 'event',
                    'metrics': {
                        'duration': 0.7000000011175871,
                    },
                    'categories': {
                        'appid': '1988',
                    },
                },
                'common': {
                    'bid': 'oec_bssdk',
                    'pid': 'https://shop.tiktok.com/view/product/1733957732396402462',
                    'view_id': 'https://shop.tiktok.com/view/product/1733957732396402462_1778875880682',
                    'user_id': '4f76b5ce-cbfc-4f2f-a3b8-b8ce0b19f31c',
                    'device_id': '9ff9d288-42c4-474d-b607-eec2256933df',
                    'session_id': 'ac8bcd41-ba9c-4d9a-ad32-bb30a06a6667',
                    'release': '',
                    'env': 'production',
                    'url': 'https://shop.tiktok.com/view/product/1733957732396402462?region=TH&locale=zh-CN',
                    'timestamp': 1778875894604,
                    'sdk_version': '1.12.1',
                    'sdk_name': 'SDK_SLARDAR_WEB',
                    'context': {},
                    'network_type': '3g',
                },
            },
        ],
    }

    response = requests.post(
        'https://mon-va.byteoversea.com/monitor_browser/collect/batch/',
        params=params,
        headers=headers,
        json=json_data,
    )

    # Note: json_data will not be serialized by requests
    # exactly as it was in the original request.
    # data = '{"ev_type":"batch","list":[{"ev_type":"custom","payload":{"name":"bssdk_unisec_core_gen_core_signature","type":"event","categories":{"appid":"1988"}},"common":{"bid":"oec_bssdk","pid":"https://shop.tiktok.com/view/product/1733957732396402462","view_id":"https://shop.tiktok.com/view/product/1733957732396402462_1778875880682","user_id":"4f76b5ce-cbfc-4f2f-a3b8-b8ce0b19f31c","device_id":"9ff9d288-42c4-474d-b607-eec2256933df","session_id":"ac8bcd41-ba9c-4d9a-ad32-bb30a06a6667","release":"","env":"production","url":"https://shop.tiktok.com/view/product/1733957732396402462?region=TH&locale=zh-CN","timestamp":1778875894603,"sdk_version":"1.12.1","sdk_name":"SDK_SLARDAR_WEB","context":{},"network_type":"3g"}},{"ev_type":"custom","payload":{"name":"bssdk_unisec_core_gen_core_signature_duration","type":"event","metrics":{"duration":0.7000000011175871},"categories":{"appid":"1988"}},"common":{"bid":"oec_bssdk","pid":"https://shop.tiktok.com/view/product/1733957732396402462","view_id":"https://shop.tiktok.com/view/product/1733957732396402462_1778875880682","user_id":"4f76b5ce-cbfc-4f2f-a3b8-b8ce0b19f31c","device_id":"9ff9d288-42c4-474d-b607-eec2256933df","session_id":"ac8bcd41-ba9c-4d9a-ad32-bb30a06a6667","release":"","env":"production","url":"https://shop.tiktok.com/view/product/1733957732396402462?region=TH&locale=zh-CN","timestamp":1778875894604,"sdk_version":"1.12.1","sdk_name":"SDK_SLARDAR_WEB","context":{},"network_type":"3g"}}]}'
    # response = requests.post(
    #    'https://mon-va.byteoversea.com/monitor_browser/collect/batch/',
    #    params=params,
    #    headers=headers,
    #    data=data,
    # )
    print(response.text)

def batch2():
    import requests

    headers = {
        'accept': '*/*',
        'accept-language': 'zh-CN,zh;q=0.9,vi;q=0.8',
        'content-type': 'application/json',
        'origin': 'https://shop.tiktok.com',
        'priority': 'u=1, i',
        'referer': 'https://shop.tiktok.com/',
        'sec-ch-ua': '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'cross-site',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
    }

    params = {
        'biz_id': 'bytecom',
    }

    json_data = {
        'ev_type': 'batch',
        'list': [
            {
                'ev_type': 'http',
                'payload': {
                    'api': 'xhr',
                    'request': {
                        'url': 'https://shop.tiktok.com/view/product/1733957732396402462?region=TH&locale=zh-CN&__loader=%28product_name_slug%24%29%2F%28product_id%29%2Fpage&__ssrDirect=true&X-Tts-Oec-Bsid=9a8c00004e202710000007c44e200000019e2d43d66c00000001ee55099fd70aa3f92c7d0b4e8165a2a3a2a2a3a2a2a32f20e9e2a2d2bd94e7067e511c673d7e93f08f65de7bff26af23da7cd26f4e660c7751c2de4439c98b1209e0e19ab729316501a600000065da3b7a7807004b01010100884e1ff093b361386743211cf820af81d2deacdc7e9a13a5a19d00919fefc1e72a110d7f7815730a744224d74d42ed047d7ee8e63a69853dee5447a01acc9d1f831bf0827fd102',
                        'method': 'get',
                        'timestamp': 1778875894603,
                    },
                    'response': {
                        'status': 200,
                        'is_custom_error': False,
                        'timestamp': 1778875895028,
                        'headers': {
                            'access-control-expose-headers': 'x-tt-traceflag,x-tt-logid',
                            'cache-control': 'max-age=0, no-cache, no-store',
                            'content-encoding': 'br',
                            'content-language': 'zh-CN',
                            'content-length': '6962',
                            'content-security-policy': 'frame-ancestors https://pearl.tiktok-row.net/ https://seller-id.tiktok.com/ https://seller-id.tokopedia.com/ https://seller-uk.tiktok.com/ https://pearl.bytedance.net/ https://boei18n-ads.byteoversea.net/ https://ads.tiktok.com/ https://*.tiktok.com/ https://oec-partner-boe.byteintl.net/ https://partner.tiktokshop.com/ https://partner.eu.tiktokshop.com/ https://partner.us.tiktokshop.com/ https://*.tiktokglobalshop.com/',
                            'content-security-policy-report-only': "report-to slardar-endpoint; script-src 'unsafe-eval' 'report-sample' 'nonce-e1a0e225634c2e59a32cf23e96cc5748-argus' 'strict-dynamic';",
                            'content-type': 'application/json; charset=utf-8',
                            'date': 'Fri, 15 May 2026 20:11:34 GMT',
                            'expires': 'Fri, 15 May 2026 20:11:34 GMT',
                            'pragma': 'no-cache',
                            'reporting-endpoints': 'slardar-endpoint="https://mon-va.byteoversea.com/monitor_browser/collect/batch/security/?bid=bytecom"',
                            'server': 'TLB',
                            'server-timing': 'inner; dur=188,bd-edenx-server-loader-(product_name_slug$)_(product_id)_page; dur=153.000116, bd-edenx-server-loader-navigation; dur=158.99992, cdn-cache; desc=MISS, edge; dur=0, origin; dur=246',
                            'x-akamai-request-id': '2907754c',
                            'x-bytefaas-execution-duration': '184.23',
                            'x-bytefaas-request-id': '2026051604113429C322A26D02D50DEF6B',
                            'x-cache': 'TCP_MISS from a23-200-145-100.deploy.akamaitechnologies.com (AkamaiGHost/22.5.0.1-8a6cb9ae5b7c562eeba48faa6e795939) (-)',
                            'x-gw-dst-psm': 'i18n_ecom_fe.growth.pdp_h5_v1',
                            'x-modernjs-response': 'yes',
                            'x-origin-response-time': '246,23.200.145.100',
                            'x-powered-by': 'Goofy Node',
                            'x-tt-logid': '2026051604113429C322A26D02D50DEF6B',
                            'x-tt-trace-host': '01e4d8b2a4b37e0b40f19a26cb14023c84d1554114343504b33bd06bf8ae16f6d3827a26bdfa22900e0849b5c7efbd98c3cc692c9713571b1c73b0bcfed8912abeef91e7adf585ba4f61da72773c99e48a2948004b030936cedec22454d07f0761',
                            'x-tt-trace-id': '00-26051604113429C322A26D02D50DEF6B-3B5B601675956C59-00',
                            'x-tt-trace-tag': 'id=16;cdn-cache=hit;type=dyn',
                        },
                        'timing': {
                            'name': 'https://shop.tiktok.com/view/product/1733957732396402462?region=TH&locale=zh-CN&__loader=%28product_name_slug%24%29%2F%28product_id%29%2Fpage&__ssrDirect=true&X-Tts-Oec-Bsid=9a8c00004e202710000007c44e200000019e2d43d66c00000001ee55099fd70aa3f92c7d0b4e8165a2a3a2a2a3a2a2a32f20e9e2a2d2bd94e7067e511c673d7e93f08f65de7bff26af23da7cd26f4e660c7751c2de4439c98b1209e0e19ab729316501a600000065da3b7a7807004b01010100884e1ff093b361386743211cf820af81d2deacdc7e9a13a5a19d00919fefc1e72a110d7f7815730a744224d74d42ed047d7ee8e63a69853dee5447a01acc9d1f831bf0827fd102',
                            'entryType': 'resource',
                            'startTime': 14986,
                            'duration': 422,
                            'initiatorType': 'xmlhttprequest',
                            'deliveryType': '',
                            'nextHopProtocol': 'h2',
                            'renderBlockingStatus': 'non-blocking',
                            'contentType': 'application/json',
                            'contentEncoding': 'br',
                            'workerStart': 14986.199999999255,
                            'workerRouterEvaluationStart': 0,
                            'workerCacheLookupStart': 0,
                            'workerMatchedSourceType': '',
                            'workerFinalSourceType': '',
                            'redirectStart': 0,
                            'redirectEnd': 0,
                            'fetchStart': 14986.299999998882,
                            'domainLookupStart': 14986.299999998882,
                            'domainLookupEnd': 14986.299999998882,
                            'connectStart': 14986.299999998882,
                            'secureConnectionStart': 14986.299999998882,
                            'connectEnd': 14986.299999998882,
                            'requestStart': 14987,
                            'responseStart': 15406.799999998882,
                            'firstInterimResponseStart': 0,
                            'finalResponseHeadersStart': 15406.799999998882,
                            'responseEnd': 15408,
                            'transferSize': 7262,
                            'encodedBodySize': 6962,
                            'decodedBodySize': 61806,
                            'responseStatus': 200,
                            'serverTiming': [
                                {
                                    'name': 'inner',
                                    'duration': 188,
                                    'description': '',
                                },
                                {
                                    'name': 'bd-edenx-server-loader-',
                                    'duration': 153.000116,
                                    'description': '',
                                },
                                {
                                    'name': 'bd-edenx-server-loader-navigation',
                                    'duration': 158.99992,
                                    'description': '',
                                },
                                {
                                    'name': 'cdn-cache',
                                    'duration': 0,
                                    'description': 'MISS',
                                },
                                {
                                    'name': 'edge',
                                    'duration': 0,
                                    'description': '',
                                },
                                {
                                    'name': 'origin',
                                    'duration': 246,
                                    'description': '',
                                },
                            ],
                        },
                    },
                    'duration': 425,
                },
                'common': {
                    'bid': 'bytecom',
                    'user_id': '7633754080074614280',
                    'device_id': '307d711b-af1c-43c8-95b4-b3f13f444a4a',
                    'session_id': 'a14e6975-32bd-426c-8330-c3d458edc404',
                    'release': '1.0.0.6350',
                    'env': 'production',
                    'url': 'https://shop.tiktok.com/view/product/1733957732396402462?region=TH&locale=zh-CN',
                    'timestamp': 1778875894603,
                    'sdk_version': '1.16.6',
                    'sdk_name': 'SDK_SLARDAR_WEB',
                    'pid': 'product_detail',
                    'view_id': 'product_detail_1778875881043',
                    'context': {
                        'canonical_url': 'https://shop.tiktok.com/view/product/1733957732396402462',
                        'enter_method': '',
                        'first_entrance': 'product_detail',
                        'first_entrance_position': '',
                        'first_entrance_tt_scene': 'internal_platform',
                        'has_ttwid': 'true',
                        'is_api': 'false',
                        'previous_page': 'product_detail',
                        'query_source': '',
                        'query_traffic_type': 'internal_platform',
                        'referer': 'https://shop.tiktok.com/view/product/1733957732396402462?region=TH&locale=zh-CN',
                        'referer_type': 'product_detail',
                        'request_url': 'https://shop.tiktok.com/view/product/1733957732396402462?region=TH&locale=zh-CN&__loader=%28product_name_slug%24%29%2F%28product_id%29%2Fpage&__ssrDirect=true&X-Tts-Oec-Bsid=9a8c00004e202710000007c44e200000019e2d43d66c00000001ee55099fd70aa3f92c7d0b4e8165a2a3a2a2a3a2a2a32f20e9e2a2d2bd94e7067e511c673d7e93f08f65de7bff26af23da7cd26f4e660c7751c2de4439c98b1209e0e19ab729316501a600000065da3b7a7807004b01010100884e1ff093b361386743211cf820af81d2deacdc7e9a13a5a19d00919fefc1e72a110d7f7815730a744224d74d42ed047d7ee8e63a69853dee5447a01acc9d1f831bf0827fd102',
                        'route_page_name': 'product',
                        'route_product_id': '1733957732396402462',
                        'route_product_name_slug': '',
                        'host': 'shop.tiktok.com',
                        'path_region': 'GLOBAL',
                        'page_name': 'product_detail',
                        'page_version_tag': '5',
                        'page_module': 'view',
                        'ip_region': 'HK',
                        'real_region': 'TH',
                        'real_region_source': 'SALE_REGION',
                        'is_bot': 'false',
                        'is_mock_bot': 'false',
                        'csr_downgrade': 'true',
                        'risk_level': 'low',
                        'risk_reasons': '',
                        'ttap_is_actual_fmp_reported': 'true',
                    },
                    'network_type': '3g',
                    'sample_rate': 1,
                },
            },
        ],
    }

    response = requests.post('https://mon.tiktokv.com/monitor_browser/collect/batch/', params=params, headers=headers,
                             json=json_data)

    # Note: json_data will not be serialized by requests
    # exactly as it was in the original request.
    # data = '{"ev_type":"batch","list":[{"ev_type":"http","payload":{"api":"xhr","request":{"url":"https://shop.tiktok.com/view/product/1733957732396402462?region=TH&locale=zh-CN&__loader=%28product_name_slug%24%29%2F%28product_id%29%2Fpage&__ssrDirect=true&X-Tts-Oec-Bsid=9a8c00004e202710000007c44e200000019e2d43d66c00000001ee55099fd70aa3f92c7d0b4e8165a2a3a2a2a3a2a2a32f20e9e2a2d2bd94e7067e511c673d7e93f08f65de7bff26af23da7cd26f4e660c7751c2de4439c98b1209e0e19ab729316501a600000065da3b7a7807004b01010100884e1ff093b361386743211cf820af81d2deacdc7e9a13a5a19d00919fefc1e72a110d7f7815730a744224d74d42ed047d7ee8e63a69853dee5447a01acc9d1f831bf0827fd102","method":"get","timestamp":1778875894603},"response":{"status":200,"is_custom_error":false,"timestamp":1778875895028,"headers":{"access-control-expose-headers":"x-tt-traceflag,x-tt-logid","cache-control":"max-age=0, no-cache, no-store","content-encoding":"br","content-language":"zh-CN","content-length":"6962","content-security-policy":"frame-ancestors https://pearl.tiktok-row.net/ https://seller-id.tiktok.com/ https://seller-id.tokopedia.com/ https://seller-uk.tiktok.com/ https://pearl.bytedance.net/ https://boei18n-ads.byteoversea.net/ https://ads.tiktok.com/ https://*.tiktok.com/ https://oec-partner-boe.byteintl.net/ https://partner.tiktokshop.com/ https://partner.eu.tiktokshop.com/ https://partner.us.tiktokshop.com/ https://*.tiktokglobalshop.com/","content-security-policy-report-only":"report-to slardar-endpoint; script-src \'unsafe-eval\' \'report-sample\' \'nonce-e1a0e225634c2e59a32cf23e96cc5748-argus\' \'strict-dynamic\';","content-type":"application/json; charset=utf-8","date":"Fri, 15 May 2026 20:11:34 GMT","expires":"Fri, 15 May 2026 20:11:34 GMT","pragma":"no-cache","reporting-endpoints":"slardar-endpoint=\\"https://mon-va.byteoversea.com/monitor_browser/collect/batch/security/?bid=bytecom\\"","server":"TLB","server-timing":"inner; dur=188,bd-edenx-server-loader-(product_name_slug$)_(product_id)_page; dur=153.000116, bd-edenx-server-loader-navigation; dur=158.99992, cdn-cache; desc=MISS, edge; dur=0, origin; dur=246","x-akamai-request-id":"2907754c","x-bytefaas-execution-duration":"184.23","x-bytefaas-request-id":"2026051604113429C322A26D02D50DEF6B","x-cache":"TCP_MISS from a23-200-145-100.deploy.akamaitechnologies.com (AkamaiGHost/22.5.0.1-8a6cb9ae5b7c562eeba48faa6e795939) (-)","x-gw-dst-psm":"i18n_ecom_fe.growth.pdp_h5_v1","x-modernjs-response":"yes","x-origin-response-time":"246,23.200.145.100","x-powered-by":"Goofy Node","x-tt-logid":"2026051604113429C322A26D02D50DEF6B","x-tt-trace-host":"01e4d8b2a4b37e0b40f19a26cb14023c84d1554114343504b33bd06bf8ae16f6d3827a26bdfa22900e0849b5c7efbd98c3cc692c9713571b1c73b0bcfed8912abeef91e7adf585ba4f61da72773c99e48a2948004b030936cedec22454d07f0761","x-tt-trace-id":"00-26051604113429C322A26D02D50DEF6B-3B5B601675956C59-00","x-tt-trace-tag":"id=16;cdn-cache=hit;type=dyn"},"timing":{"name":"https://shop.tiktok.com/view/product/1733957732396402462?region=TH&locale=zh-CN&__loader=%28product_name_slug%24%29%2F%28product_id%29%2Fpage&__ssrDirect=true&X-Tts-Oec-Bsid=9a8c00004e202710000007c44e200000019e2d43d66c00000001ee55099fd70aa3f92c7d0b4e8165a2a3a2a2a3a2a2a32f20e9e2a2d2bd94e7067e511c673d7e93f08f65de7bff26af23da7cd26f4e660c7751c2de4439c98b1209e0e19ab729316501a600000065da3b7a7807004b01010100884e1ff093b361386743211cf820af81d2deacdc7e9a13a5a19d00919fefc1e72a110d7f7815730a744224d74d42ed047d7ee8e63a69853dee5447a01acc9d1f831bf0827fd102","entryType":"resource","startTime":14986,"duration":422,"initiatorType":"xmlhttprequest","deliveryType":"","nextHopProtocol":"h2","renderBlockingStatus":"non-blocking","contentType":"application/json","contentEncoding":"br","workerStart":14986.199999999255,"workerRouterEvaluationStart":0,"workerCacheLookupStart":0,"workerMatchedSourceType":"","workerFinalSourceType":"","redirectStart":0,"redirectEnd":0,"fetchStart":14986.299999998882,"domainLookupStart":14986.299999998882,"domainLookupEnd":14986.299999998882,"connectStart":14986.299999998882,"secureConnectionStart":14986.299999998882,"connectEnd":14986.299999998882,"requestStart":14987,"responseStart":15406.799999998882,"firstInterimResponseStart":0,"finalResponseHeadersStart":15406.799999998882,"responseEnd":15408,"transferSize":7262,"encodedBodySize":6962,"decodedBodySize":61806,"responseStatus":200,"serverTiming":[{"name":"inner","duration":188,"description":""},{"name":"bd-edenx-server-loader-","duration":153.000116,"description":""},{"name":"bd-edenx-server-loader-navigation","duration":158.99992,"description":""},{"name":"cdn-cache","duration":0,"description":"MISS"},{"name":"edge","duration":0,"description":""},{"name":"origin","duration":246,"description":""}]}},"duration":425},"common":{"bid":"bytecom","user_id":"7633754080074614280","device_id":"307d711b-af1c-43c8-95b4-b3f13f444a4a","session_id":"a14e6975-32bd-426c-8330-c3d458edc404","release":"1.0.0.6350","env":"production","url":"https://shop.tiktok.com/view/product/1733957732396402462?region=TH&locale=zh-CN","timestamp":1778875894603,"sdk_version":"1.16.6","sdk_name":"SDK_SLARDAR_WEB","pid":"product_detail","view_id":"product_detail_1778875881043","context":{"canonical_url":"https://shop.tiktok.com/view/product/1733957732396402462","enter_method":"","first_entrance":"product_detail","first_entrance_position":"","first_entrance_tt_scene":"internal_platform","has_ttwid":"true","is_api":"false","previous_page":"product_detail","query_source":"","query_traffic_type":"internal_platform","referer":"https://shop.tiktok.com/view/product/1733957732396402462?region=TH&locale=zh-CN","referer_type":"product_detail","request_url":"https://shop.tiktok.com/view/product/1733957732396402462?region=TH&locale=zh-CN&__loader=%28product_name_slug%24%29%2F%28product_id%29%2Fpage&__ssrDirect=true&X-Tts-Oec-Bsid=9a8c00004e202710000007c44e200000019e2d43d66c00000001ee55099fd70aa3f92c7d0b4e8165a2a3a2a2a3a2a2a32f20e9e2a2d2bd94e7067e511c673d7e93f08f65de7bff26af23da7cd26f4e660c7751c2de4439c98b1209e0e19ab729316501a600000065da3b7a7807004b01010100884e1ff093b361386743211cf820af81d2deacdc7e9a13a5a19d00919fefc1e72a110d7f7815730a744224d74d42ed047d7ee8e63a69853dee5447a01acc9d1f831bf0827fd102","route_page_name":"product","route_product_id":"1733957732396402462","route_product_name_slug":"","host":"shop.tiktok.com","path_region":"GLOBAL","page_name":"product_detail","page_version_tag":"5","page_module":"view","ip_region":"HK","real_region":"TH","real_region_source":"SALE_REGION","is_bot":"false","is_mock_bot":"false","csr_downgrade":"true","risk_level":"low","risk_reasons":"","ttap_is_actual_fmp_reported":"true"},"network_type":"3g","sample_rate":1}}]}'
    # response = requests.post('https://mon.tiktokv.com/monitor_browser/collect/batch/', params=params, headers=headers, data=data)
    print(response.text)

if __name__ == '__main__':
    batch1()
    print('======')
    batch2()


