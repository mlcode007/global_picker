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
    };
  }

  // 从插件搜索响应里取出嵌套在 responseInfo 字符串中的 offerList
  function extractOfferListMap(data) {
    const map = {};
    let offerList = null;

    if (data.offerList && Array.isArray(data.offerList)) {
      offerList = data.offerList;
    } else if (data.responseInfo && typeof data.responseInfo.imageSearchOfferResultViewService === 'string') {
      try {
        const inner = JSON.parse(data.responseInfo.imageSearchOfferResultViewService);
        if (inner && inner.data && Array.isArray(inner.data.offerList)) {
          offerList = inner.data.offerList;
        }
      } catch (e) {
        console.log('[1688采集] 解析 responseInfo.offerList 失败:', e.message);
      }
    }

    if (offerList) {
      for (const offer of offerList) {
        const parsed = parseOfferListItem(offer);
        if (parsed.offerId) map[parsed.offerId] = parsed;
      }
    }
    return map;
  }

  function parse1688Data(responseData) {
    if (!responseData || !responseData.data) {
      return [];
    }

    const data = responseData.data;
    const products = [];

    // offerList(含价格)按 offerId 建索引，用于给 offerExtend 补充价格/标题/图片
    const offerListMap = extractOfferListMap(data);

    // 详情/插件搜索格式: offerExtend（销量、店铺、好评等），价格需从 offerList 合并
    if (data.offerExtend) {
      const offerExtend = data.offerExtend;
      const offerMember = data.offerMember || {};

      for (const [offerId, extendData] of Object.entries(offerExtend)) {
        const saleStats = extendData.saleStatsModel || {};
        const shopInfo = extendData.shopInfoModel || {};
        const images = extendData.images || [];
        const fromList = offerListMap[String(offerId)] || {};

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
        });
      }
      return products;
    }

    // 纯 offerList 格式（无 offerExtend 时的兜底）
    for (const item of Object.values(offerListMap)) {
      products.push({
        offerId: item.offerId,
        memberId: '',
        title: item.title,
        images: item.images,
        mainImage: item.mainImage,
        price: item.price,
        consignPrice: item.consignPrice,
        last30DaysSales: '',
        totalSales: '',
        last30DaysDropShippingSales: '',
        goodRates: 0,
        repurchaseRate: item.repurchaseRate,
        collectionRate24h: '',
        earliestListingTime: '',
        latestUpdateTime: '',
        freeReturnIn7d: item.freeReturnIn7d,
        tpYear: item.tpYear,
        consignmentSales30d: '',
        shiliType: item.shiliType,
        supportWaybill: '',
      });
    }

    return products;
  }

  function listenForInterceptedData() {
    document.addEventListener('__1688_intercept_data', (e) => {
      const detail = e.detail || {};
      const type = detail.type;
      const url = detail.url;

      // MAIN 世界以 JSON 字符串形式跨 world 传递数据，这里解析回对象
      let data = null;
      try {
        data = detail.json ? JSON.parse(detail.json) : (detail.data || null);
      } catch (parseErr) {
        console.log('[1688采集] 拦截数据 JSON 解析失败:', parseErr.message);
        return;
      }

      const hasOfferExtend = data && data.data && data.data.offerExtend;
      const hasOfferList = data && data.data && data.data.offerList && Array.isArray(data.data.offerList);
      const hasNestedOfferList = data && data.data && data.data.responseInfo &&
        typeof data.data.responseInfo.imageSearchOfferResultViewService === 'string';
      const hitCount = hasOfferExtend ? Object.keys(data.data.offerExtend).length : (hasOfferList ? data.data.offerList.length : 0);
      console.log('[1688采集] 收到MAIN世界拦截数据, 请求类型:', type, '商品数:', hitCount);

      if (hasOfferExtend || hasOfferList || hasNestedOfferList) {
        const products = parse1688Data(data);
        console.log('[1688采集] 解析到商品数据, 数量:', products.length);

        // 打印所有商品详细信息
        console.log('========== 1688商品数据 ==========');
        products.forEach((p, idx) => {
          console.log(`--- 商品 ${idx + 1} ---`);
          console.log('  currentTikTokProductId:', currentTikTokProductId);
          console.log('  offerId:', p.offerId);
          console.log('  title:', p.title);
          console.log('  price(代发价优先):', p.price);
          console.log('  mainImage:', p.mainImage);
          console.log('  tpYear:', p.tpYear);
          console.log('  shiliType:', p.shiliType);
          console.log('  freeReturnIn7d:', p.freeReturnIn7d);
          console.log('  repurchaseRate:', p.repurchaseRate);
          console.log('  last30DaysSales:', p.last30DaysSales);
          console.log('  totalSales:', p.totalSales);
          console.log('  goodRates:', p.goodRates);
          console.log('');
        });
        console.log('==================================');

        // 直接发送给后台入库；归属商品(product_id/tiktok_product_id)由后台
        // 从 gp_1688_context 上下文补全，collector 自身不强依赖这两个 ID。
        sendProductsToBackend(products);
      } else {
        console.log('[1688采集] 响应数据格式不匹配');
      }
    });
    console.log('[1688采集] MAIN世界数据监听器已注册');
  }

  function sendProductsToBackend(products) {
    // 归属商品优先用消息设置的值；拿不到时从共享存储 gp_1688_context 读取
    // （sync-inject 在触发同款比价时写入），最终仍由后台兜底补全。
    chrome.storage.local.get('gp_1688_context', (res) => {
      const ctx = (res && res.gp_1688_context) || {};
      const productId = currentProductId != null ? currentProductId : (ctx.productId != null ? ctx.productId : null);
      const tiktokProductId = currentTikTokProductId != null ? currentTikTokProductId : (ctx.tiktokProductId != null ? ctx.tiktokProductId : null);
      const syncLimit = ctx.syncLimit != null ? ctx.syncLimit : undefined;

      console.log('[1688采集] 准备入库, productId:', productId, 'tiktokProductId:', tiktokProductId, '商品数:', products.length, 'syncLimit:', syncLimit);

      chrome.runtime.sendMessage({
        type: MESSAGE_TYPES.SAVE_1688_DATA,
        data: {
          tiktokProductId: tiktokProductId,
          productId: productId,
          products: products,
          syncLimit: syncLimit,
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
