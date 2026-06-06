/**
 * 1688 采集脚本 - TikTok页面版本
 * 运行在 TikTok Shop 商品页，拦截1688插件的API请求
 * 
 * 关键：1688内部代码把 window.fetch 包装成了 HookBX$1.window.fetch
 * 必须拦截 HookBX$1.window.fetch 才能生效
 */

(function () {
  'use strict';

  // 幂等守卫：声明式注入与后台 scripting.executeScript 主动注入可能同时发生，
  // 避免重复注册 message 监听 / 定时器导致重复处理。
  if (window.__GP_1688_COLLECTOR__) {
    return;
  }
  window.__GP_1688_COLLECTOR__ = true;

  const MESSAGE_TYPES = {
    SAVE_1688_DATA: 'SAVE_1688_DATA',
    CLOSE_1688_PLUGIN: 'CLOSE_1688_PLUGIN',
    COLLECTION_COMPLETE: 'COLLECTION_COMPLETE',
    CLICK_CLOSE_BUTTON: 'CLICK_CLOSE_BUTTON',
  };

  let isCollecting = false;
  let currentTikTokProductId = null;
  let currentProductId = null;
  let pendingProducts = []; // 缓冲队列：等ID设置后再发送

  const isInIframe = window !== window.top;
  const is1688Domain = window.location.hostname.includes('1688.com');

  // 把 offerList 单条解析成统一字段（含价格/标题/图片/店铺信息）
  function parseOfferListItem(offer) {
    const info = offer.information || {};
    const priceInfo = (offer.tradePrice && offer.tradePrice.offerPrice && offer.tradePrice.offerPrice.priceInfo) || {};
    const tradeService = offer.tradeService || {};
    const company = offer.company || {};
    const image = offer.image || {};

    // 代发价(consignPrice)优先，作为比价/利润计算的基准；否则用展示价 price
    const consignPrice = parseFloat(priceInfo.consignPrice) || 0;
    const showPrice = parseFloat(priceInfo.price) || 0;
    const price = consignPrice || showPrice || 0;

    return {
      offerId: String(offer.id || ''),
      title: info.subject || info.simpleSubject || '',
      mainImage: image.imgUrl || '',
      images: [image.imgUrl || ''].filter(Boolean),
      price: price,
      consignPrice: consignPrice,
      repurchaseRate: info.rePurchaseRate || '',
      freeReturnIn7d: tradeService.sevenDaysReturn ? '是' : '',
      tpYear: tradeService.tpYear || 0,
      shiliType: company.isSuperFactory ? '超级工厂' : (company.bizTypeName || ''),
      companyName: company.name || '',
    };
  }

  // 1688 插件搜索响应结构（见 product_1688_old4.json）：
  //   商品数据 → data.responseInfo.imageSearchOfferResultViewService → data.offerList
  //   快递数据 → data.offerExtend[offerId].deliveryChargeInfo

  function parseImageSearchViewService(svc) {
    if (!svc) return null;
    if (typeof svc === 'string') {
      try { return JSON.parse(svc); } catch (e) { return null; }
    }
    if (typeof svc === 'object') return svc;
    return null;
  }

  // 从 responseInfo.imageSearchOfferResultViewService 提取商品列表（保持页面顺序）
  function extractOfferListFromImageSearch(data) {
    const svc = data.responseInfo && data.responseInfo.imageSearchOfferResultViewService;
    const parsed = parseImageSearchViewService(svc);
    if (parsed && parsed.data && Array.isArray(parsed.data.offerList)) {
      return parsed.data.offerList;
    }
    if (data.offerList && Array.isArray(data.offerList)) {
      return data.offerList;
    }
    return [];
  }

  // 从原始 JSON 文本的 offerExtend 段补全 deliveryChargeInfo（防止解析后字段缺失）
  function extractDciMapFromRaw(rawJson) {
    const map = {};
    if (!rawJson || typeof rawJson !== 'string') return map;
    const oeStart = rawJson.indexOf('"offerExtend"');
    if (oeStart < 0) return map;
    const section = rawJson.substring(oeStart, oeStart + 200000);
    const offerRe = /"(\d{10,})"\s*:/g;
    let m;
    while ((m = offerRe.exec(section)) !== null) {
      const offerId = m[1];
      const dciKey = '"deliveryChargeInfo"';
      const dciStart = section.indexOf(dciKey, m.index);
      if (dciStart < 0 || dciStart > m.index + 15000) continue;
      const braceStart = section.indexOf('{', dciStart + dciKey.length);
      if (braceStart < 0) continue;
      let depth = 0;
      let dci = null;
      for (let i = braceStart; i < section.length; i++) {
        if (section[i] === '{') depth++;
        else if (section[i] === '}') {
          depth--;
          if (depth === 0) {
            try { dci = JSON.parse(section.slice(braceStart, i + 1)); } catch (e) { /* ignore */ }
            break;
          }
        }
      }
      if (dci) map[offerId] = dci;
    }
    return map;
  }

  function hydrateOfferExtendDci(data, rawJson) {
    if (!data || !data.offerExtend || !rawJson) return;
    const dciMap = extractDciMapFromRaw(rawJson);
    for (const [offerId, ext] of Object.entries(data.offerExtend)) {
      if (!ext.deliveryChargeInfo && dciMap[offerId]) {
        ext.deliveryChargeInfo = dciMap[offerId];
      }
    }
  }

  function countDciInPayload(data) {
    if (!data || !data.data || !data.data.offerExtend) return 0;
    return Object.values(data.data.offerExtend).filter((e) => e && e.deliveryChargeInfo).length;
  }

  function mergePayloadData(base, incoming) {
    if (!incoming || !incoming.data) return base;
    if (!base || !base.data) return incoming;
    const merged = { ...base, data: { ...base.data, ...incoming.data } };
    if (incoming.data.responseInfo && !merged.data.responseInfo) {
      merged.data.responseInfo = incoming.data.responseInfo;
    }
    if (base.data.offerExtend && incoming.data.offerExtend) {
      merged.data.offerExtend = { ...base.data.offerExtend };
      for (const [offerId, ext] of Object.entries(incoming.data.offerExtend)) {
        const prev = merged.data.offerExtend[offerId] || {};
        merged.data.offerExtend[offerId] = {
          ...prev,
          ...ext,
          deliveryChargeInfo: ext.deliveryChargeInfo || prev.deliveryChargeInfo,
        };
      }
    } else if (incoming.data.offerExtend) {
      merged.data.offerExtend = incoming.data.offerExtend;
    }
    return merged;
  }

  // DOM 兜底：1688 插件卡片上展示的邮费文字
  function scrapeFreightFromDom() {
    const map = {};
    try {
      document.querySelectorAll('a[href*="detail.1688.com/offer/"], a[href*="/offer/"]').forEach((a) => {
        const href = a.getAttribute('href') || '';
        const m = href.match(/offer\/(\d{10,})/);
        if (!m) return;
        const offerId = m[1];
        let card = a;
        for (let i = 0; i < 12 && card; i++) {
          const text = (card.innerText || '').replace(/\s+/g, ' ');
          if (!text || text.length > 3000) {
            card = card.parentElement;
            continue;
          }
          if (text.includes('包邮')) {
            map[offerId] = { isFreeShipping: true, minFreight: 0 };
            break;
          }
          const freightMatch =
            text.match(/(?:运费|邮费|快递)[^¥\d]{0,10}¥?\s*(\d+(?:\.\d+)?)\s*(?:起)?/) ||
            text.match(/¥\s*(\d+(?:\.\d+)?)\s*起(?:邮|运费)?/);
          if (freightMatch) {
            map[offerId] = { isFreeShipping: false, minFreight: parseFloat(freightMatch[1]) };
            break;
          }
          card = card.parentElement;
        }
      });
    } catch (e) { /* ignore */ }
    return map;
  }

  function applyDomFreightFallback(products) {
    const domMap = scrapeFreightFromDom();
    const hitCount = Object.keys(domMap).length;
    if (!hitCount) return products;
    console.log('[1688采集-邮费] DOM 兜底命中:', hitCount);
    return products.map((p) => {
      if (p.isFreeShipping || (p.minFreight && p.minFreight > 0)) return p;
      const dom = domMap[String(p.offerId)];
      if (!dom) return p;
      return { ...p, isFreeShipping: dom.isFreeShipping, minFreight: dom.minFreight };
    });
  }

  const interceptBuffer = {
    data: null,
    rawJson: null,
    page: 1,
    timer: null,
    flushed: false,
  };

  function flushInterceptBuffer() {
    interceptBuffer.timer = null;
    if (interceptBuffer.flushed || !interceptBuffer.data) return;
    interceptBuffer.flushed = true;

    const data = interceptBuffer.data;
    const page = interceptBuffer.page;
    interceptBuffer.data = null;
    interceptBuffer.rawJson = null;

    if (!data.data || !data.data.offerExtend) return;
    const offerList = extractOfferListFromImageSearch(data.data);
    if (!offerList.length) {
      console.log('[1688采集] 延迟入库取消: offerList 为空');
      return;
    }

    let products = parse1688Data(data);
    products = applyDomFreightFallback(products);
    const withFreight = products.filter((p) => p.isFreeShipping || p.minFreight > 0).length;
    console.log('[1688采集] 延迟入库, 商品数:', products.length, '含邮费:', withFreight, 'page:', page);

    console.log('========== 1688商品数据 ==========');
    products.forEach((p, idx) => {
      console.log(`--- 商品 ${idx + 1} --- offerId=${p.offerId} price=${p.price} isFree=${p.isFreeShipping} minFreight=${p.minFreight}`);
    });
    console.log('==================================');

    sendProductsToBackend(products, page);
  }

  function scheduleBufferedSave() {
    if (interceptBuffer.timer) clearTimeout(interceptBuffer.timer);
    interceptBuffer.timer = setTimeout(flushInterceptBuffer, 3000);
  }

  // 从 offerExtend[offerId].deliveryChargeInfo 解析包邮/起邮
  function parseShippingFromExtend(extendData) {
    if (!extendData || !extendData.deliveryChargeInfo) {
      return { hasShipping: false, isFreeShipping: false, minFreight: 0 };
    }
    const dci = extendData.deliveryChargeInfo;
    // templateType=1 是平台包邮模板
    if (dci.templateType === 1 && !Array.isArray(dci.costs)) {
      return { hasShipping: true, isFreeShipping: true, minFreight: 0 };
    }
    if (Array.isArray(dci.costs) && dci.costs.length > 0) {
      const totals = dci.costs
        .map(c => parseFloat(c.totalCost))
        .filter(v => !isNaN(v));
      if (totals.length > 0) {
        const min = Math.min(...totals);
        return { hasShipping: true, isFreeShipping: min === 0, minFreight: min };
      }
    }
    return { hasShipping: false, isFreeShipping: false, minFreight: 0 };
  }

  // 从 offerList 数组中提取 offerId 列表（保持原始顺序）
  function extractOfferIdsFromList(offerList) {
    const ids = [];
    for (const offer of offerList) {
      if (offer && offer.id != null) {
        ids.push(String(offer.id));
      }
    }
    return ids;
  }

  // 从 offerList 原始数组构建 (offerId -> 解析结果) 索引
  function buildOfferListMap(offerList) {
    const map = {};
    for (const offer of offerList) {
      const parsed = parseOfferListItem(offer);
      if (parsed.offerId) map[parsed.offerId] = parsed;
    }
    return map;
  }

  function parse1688Data(responseData) {
    if (!responseData || !responseData.data) {
      return [];
    }

    const data = responseData.data;

    console.log(data);


    const products = [];

    // 第二页（page > 1）不入库
    console.log('[1688采集] 当前 page =', data.page);
    if (data.page && data.page > 1) {
      console.log('[1688采集] ⏭️ 第二页数据跳过，page =', data.page);
      return products;
    }

    // 1) 商品：imageSearchOfferResultViewService → offerList
    const offerList = extractOfferListFromImageSearch(data);
    const offerListMap = buildOfferListMap(offerList);

    // 2) 快递：offerExtend[offerId].deliveryChargeInfo
    if (!data.offerExtend) {
      console.log('[1688采集] 响应无 offerExtend，无法读取快递信息');
      return products;
    }
    
    const offerExtend = data.offerExtend;
    const offerMember = data.offerMember || {};
    const orderedIds = extractOfferIdsFromList(offerList);
    const offerIds = orderedIds.length > 0 ? orderedIds : Object.keys(offerExtend);

    for (const offerId of offerIds) {
      const extendData = offerExtend[offerId];
      if (!extendData) continue;

      const saleStats = extendData.saleStatsModel || {};
      const shopInfo = extendData.shopInfoModel || {};
      const images = extendData.images || [];
      const fromList = offerListMap[String(offerId)] || {};
      const shipping = parseShippingFromExtend(extendData);

      console.log(`[1688采集-邮费] offerId=${offerId} | hasDCI=${!!extendData.deliveryChargeInfo} | isFree=${shipping.isFreeShipping} | minFreight=${shipping.minFreight}`);

        products.push({
          offerId: offerId,
          memberId: offerMember[offerId] || '',
          title: extendData.title || fromList.title || '',
          images: images.length ? images : (fromList.images || []),
          mainImage: images[0] || fromList.mainImage || '',
          price: fromList.price || 0,
          consignPrice: fromList.consignPrice || 0,
          last30DaysSales: saleStats.last30DaysSales || '',
          totalSales: saleStats.totalSales || '',
          last30DaysDropShippingSales: saleStats.last30DaysDropShippingSales || '',
          goodRates: saleStats.goodRates || 0,
          repurchaseRate: saleStats.repurchaseRate || fromList.repurchaseRate || '',
          collectionRate24h: saleStats.collectionRate24h || '',
          earliestListingTime: saleStats.earliestListingTime || '',
          latestUpdateTime: saleStats.latestUpdateTime || '',
          freeReturnIn7d: shopInfo.freeReturnIn7d || fromList.freeReturnIn7d || '',
          tpYear: shopInfo.tpYear || fromList.tpYear || 0,
          consignmentSales30d: shopInfo.consignmentSales30d || '',
          shiliType: shopInfo.shiliType || fromList.shiliType || '',
          supportWaybill: (shopInfo.surportWaybill || []).map(w => w.name).join(','),
          companyName: fromList.companyName || '',
          isFreeShipping: shipping.isFreeShipping,
          minFreight: shipping.minFreight,
        });
    }

    return products;
  }

  function listenForInterceptedData() {
    document.addEventListener('__1688_intercept_data', (e) => {
      const detail = e.detail || {};
      const type = detail.type;
      const rawJson = detail.json || (detail.data ? JSON.stringify(detail.data) : null);
      const page = detail.page || 1;

      if (page > 1) {
        console.log('[1688采集] 跳过第', page, '页');
        return;
      }

      let data = null;
      try {
        data = rawJson ? JSON.parse(rawJson) : (detail.data || null);
      } catch (parseErr) {
        console.log('[1688采集] JSON 解析失败:', parseErr.message);
        return;
      }

      if (!data || !data.data || !data.data.offerExtend) return;

      hydrateOfferExtendDci(data.data, rawJson);
      data.data.page = page;

      const offerList = extractOfferListFromImageSearch(data.data);
      const dciCount = countDciInPayload(data);
      console.log('[1688采集] 收到 type=' + type +
        ' offerList=' + offerList.length +
        ' offerExtend=' + Object.keys(data.data.offerExtend).length +
        ' 含DCI=' + dciCount +
        ' 原文含邮费=' + (rawJson ? rawJson.indexOf('deliveryChargeInfo') !== -1 : false));

      if (!offerList.length) {
        console.log('[1688采集] offerList 为空，等待后续数据');
        return;
      }

      // 合并多次拦截（网络响应 / 内存扫描 / JSON.parse 捕获），优先保留有邮费的数据
      interceptBuffer.flushed = false;
      interceptBuffer.data = mergePayloadData(interceptBuffer.data, data);
      if (!interceptBuffer.rawJson || (rawJson && rawJson.indexOf('deliveryChargeInfo') !== -1)) {
        interceptBuffer.rawJson = rawJson;
      }
      if (interceptBuffer.data && interceptBuffer.rawJson) {
        hydrateOfferExtendDci(interceptBuffer.data.data, interceptBuffer.rawJson);
      }
      interceptBuffer.page = page;

      scheduleBufferedSave();
    });
    console.log('[1688采集] MAIN世界数据监听器已注册');
  }

  function sendProductsToBackend(products, page) {
    // 归属商品优先用消息设置的值；拿不到时从共享存储 gp_1688_context 读取
    // （sync-inject 在触发同款比价时写入），最终仍由后台兜底补全。
    chrome.storage.local.get('gp_1688_context', (res) => {
      const ctx = (res && res.gp_1688_context) || {};
      const productId = currentProductId != null ? currentProductId : (ctx.productId != null ? ctx.productId : null);
      const tiktokProductId = currentTikTokProductId != null ? currentTikTokProductId : (ctx.tiktokProductId != null ? ctx.tiktokProductId : null);
      const syncLimit = ctx.syncLimit != null ? ctx.syncLimit : undefined;

      console.log('[1688采集] 准备入库, productId:', productId, 'tiktokProductId:', tiktokProductId, '商品数:', products.length, 'syncLimit:', syncLimit, 'page:', page);

      chrome.runtime.sendMessage({
        type: MESSAGE_TYPES.SAVE_1688_DATA,
        data: {
          tiktokProductId: tiktokProductId,
          productId: productId,
          products: products,
          syncLimit: syncLimit,
          page: page,
          timestamp: Date.now(),
        },
      }, (saveResponse) => {
        if (chrome.runtime.lastError) {
          console.error('[1688采集] 发送数据失败:', chrome.runtime.lastError.message);
        } else if (saveResponse && saveResponse.success) {
          console.log('[1688采集] ✅ 数据保存成功');
        } else {
          console.error('[1688采集] ❌ 入库失败:', saveResponse && saveResponse.error);
        }
      });
    });
  }

  function setCollecting(state) {
    isCollecting = state.isCollecting;
    currentTikTokProductId = state.tiktokProductId;
    currentProductId = state.productId;
    console.log('[1688采集] 设置采集状态, isCollecting:', isCollecting, 'TikTok商品ID:', currentTikTokProductId);

    // 发送缓冲的数据
    if (pendingProducts.length > 0) {
      console.log('[1688采集] 发送缓冲数据, 批次:', pendingProducts.length);
      pendingProducts.forEach(batch => sendProductsToBackend(batch));
      pendingProducts = [];
    }
  }

  if (is1688Domain) {
    console.log('[1688采集] 运行在1688 iframe内');
    console.log('[1688采集] 当前域名:', window.location.hostname);
    console.log('[1688采集] 当前URL:', window.location.href);

    // MAIN 世界拦截器已通过 manifest 声明式注入(inject_main.js, world: MAIN, document_start)
    // 这里仅注册跨 world 数据监听器，接收拦截到的响应
    listenForInterceptedData();

    // 只在1688 iframe中注册消息监听器
    chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
      if (message.type === 'START_1688_COLLECTION') {
        setCollecting({
          isCollecting: true,
          tiktokProductId: message.data.tiktokProductId,
          productId: message.data.productId,
        });
        sendResponse({ success: true });
      } else if (message.type === 'STOP_1688_COLLECTION') {
        isCollecting = false;
        currentTikTokProductId = null;
        currentProductId = null;
        pendingProducts = [];
        console.log('[1688采集] 停止采集');
        sendResponse({ success: true });
      }
      return true;
    });

    window.addEventListener('message', (event) => {
      if (event.data && event.data.type === 'START_1688_COLLECTION') {
        setCollecting({
          isCollecting: true,
          tiktokProductId: event.data.data.tiktokProductId,
          productId: event.data.data.productId,
        });
      } else if (event.data && event.data.type === 'CLOSE_1688_PLUGIN') {
        console.log('[1688采集] 收到关闭指令');

        function clickCloseButton() {
          const closeBtns = document.querySelectorAll('[class*="close-icon"]');
          if (closeBtns && closeBtns.length > 0) {
            closeBtns.forEach((btn) => btn.click());
            return true;
          }
          return false;
        }

        if (!clickCloseButton()) {
          setTimeout(() => {
            if (!clickCloseButton()) {
              setTimeout(() => {
                if (!clickCloseButton()) {
                  console.error('[1688采集] 三次尝试后仍未找到关闭按钮');
                }
              }, 1000);
            }
          }, 500);
        }
      }
    });

    const checkStorageInterval = setInterval(() => {
      chrome.storage.local.get('1688_collection_state', (result) => {
        if (result['1688_collection_state'] && result['1688_collection_state'].isCollecting && !isCollecting) {
          const state = result['1688_collection_state'];
          setCollecting({
            isCollecting: true,
            tiktokProductId: state.tiktokProductId,
            productId: state.productId,
          });
          clearInterval(checkStorageInterval);
        }
      });
    }, 500);
    setTimeout(() => clearInterval(checkStorageInterval), 10000);

  } else {
    console.log('[1688采集] 运行在TikTok页面，等待采集指令');
  }
})();
