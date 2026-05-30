import json

with open('1688_插件列表_请求.txt', 'r') as f:
    data = json.load(f)

html = data['data']['responseInfo']['imageSearchOfferResultViewService']
html_data = json.loads(html)
offer_list = html_data['data']['offerList']

for i, offer in enumerate(offer_list[:3]):
    print(f'=== Offer {i+1} ===')
    print('id:', offer.get('id'))
    print('information:', json.dumps(offer.get('information'), ensure_ascii=False)[:500])
    print('tradePrice:', json.dumps(offer.get('tradePrice'), ensure_ascii=False)[:500])
    print('company:', json.dumps(offer.get('company'), ensure_ascii=False)[:500])
    print('tradeService.tpYear:', offer.get('tradeService', {}).get('tpYear'))
    print('tradeService.sevenDaysReturn:', offer.get('tradeService', {}).get('sevenDaysReturn'))
    print()
