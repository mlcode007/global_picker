/**
 * 1688 请求拦截器 —— MAIN 世界版本
 *
 * 拦截 mtop.1688.pc.plugin.imagesearch.plugin.search 的原始响应文本，
 * 派发给 ISOLATED 世界的 alibaba1688-collector.js。
 *
 * 注意：部分环境下网络响应 offerExtend 不含 deliveryChargeInfo（~169KB），
 * 但 1688 页面内存中会在渲染后补全邮费（~187KB，见 product_1688_old4.json）。
 * 因此除网络拦截外，还会在 2.5s 后扫描页面内存中的 offerExtend。
 */

(function () {
  'use strict';

  if (window.__GP_1688_HOOK_INSTALLED__) {
    return;
  }
  window.__GP_1688_HOOK_INSTALLED__ = true;

  var TARGET_API = 'mtop.1688.pc.plugin.imagesearch.plugin.search';
  var _nativeFetch = typeof window.fetch === 'function' ? window.fetch.bind(window) : null;
  var _origJsonParse = JSON.parse;

  function isPluginSearchUrl(urlString) {
    if (!urlString) return false;
    return (
      urlString.indexOf(TARGET_API) !== -1 ||
      (urlString.indexOf('imagesearch') !== -1 && urlString.indexOf('plugin') !== -1)
    );
  }

  function isMtopUrl(urlString) {
    return urlString && urlString.indexOf('h5api.m.1688.com') !== -1 && urlString.indexOf('/h5/mtop') !== -1;
  }

  function hasOfferExtendText(text) {
    return text && typeof text === 'string' && text.indexOf('"offerExtend"') !== -1;
  }

  function dispatchData(type, url, jsonStr, pageOverride) {
    try {
      var page = pageOverride != null ? pageOverride : 1;
      try {
        var urlString = url || '';
        var m = urlString.match(/[?&]data=([^&]+)/);
        if (m) {
          var dataParam = decodeURIComponent(m[1]);
          var outer = _origJsonParse(dataParam);
          if (outer.params) {
            var inner = _origJsonParse(decodeURIComponent(outer.params));
            var bp = inner['serviceParam.extendParam[beginPage]'];
            if (bp != null) page = parseInt(bp, 10) || 1;
          }
        }
      } catch (e) {
        console.log('[1688-MAIN] 解析 beginPage 失败:', e && e.message);
      }

      console.log(
        '[1688-MAIN] 派发 type=' + type +
        ' 长度=' + jsonStr.length +
        ' 含邮费=' + (jsonStr.indexOf('deliveryChargeInfo') !== -1) +
        ' page=' + page
      );

      document.dispatchEvent(
        new CustomEvent('__1688_intercept_data', {
          detail: { type: type, url: url, json: jsonStr, page: page },
        })
      );
    } catch (e) {
      console.log('[1688-MAIN] 派发数据失败:', e && e.message);
    }
  }

  // 在页面 JS 内存中查找已补全邮费的 offerExtend
  function findOfferExtendWithDci(root, depth, seen) {
    if (!root || typeof root !== 'object' || depth > 12) return null;
    if (seen.indexOf(root) >= 0) return null;
    seen.push(root);

    try {
      if (root.offerExtend && typeof root.offerExtend === 'object') {
        var keys = Object.keys(root.offerExtend);
        for (var i = 0; i < keys.length; i++) {
          var item = root.offerExtend[keys[i]];
          if (item && item.deliveryChargeInfo) {
            return root.offerExtend;
          }
        }
      }
    } catch (e) { /* ignore */ }

    var childKeys = [];
    try { childKeys = Object.keys(root); } catch (e2) { return null; }
    for (var j = 0; j < childKeys.length && j < 80; j++) {
      try {
        var child = root[childKeys[j]];
        if (child && typeof child === 'object') {
          var found = findOfferExtendWithDci(child, depth + 1, seen);
          if (found) return found;
        }
      } catch (e3) { /* ignore */ }
    }
    return null;
  }

  var memoryScanTimer = null;
  function scheduleMemoryScan(baseJsonStr, url, page) {
    if (!baseJsonStr || baseJsonStr.indexOf('deliveryChargeInfo') !== -1) return;
    if (memoryScanTimer) clearTimeout(memoryScanTimer);
    memoryScanTimer = setTimeout(function () {
      memoryScanTimer = null;
      var oe = findOfferExtendWithDci(window, 0, []);
      if (!oe) {
        console.log('[1688-MAIN] 内存扫描: 未找到含邮费的 offerExtend');
        return;
      }
      var dciCount = 0;
      Object.keys(oe).forEach(function (id) {
        if (oe[id] && oe[id].deliveryChargeInfo) dciCount++;
      });
      console.log('[1688-MAIN] 内存扫描: 找到含邮费 offerExtend 数量:', dciCount);
      try {
        var base = _origJsonParse(baseJsonStr);
        if (base && base.data) {
          base.data.offerExtend = oe;
          dispatchData('memory-merge', url, JSON.stringify(base), page);
        }
      } catch (e) {
        console.log('[1688-MAIN] 内存合并失败:', e && e.message);
      }
    }, 2500);
  }

  function handleInterceptText(type, urlString, text) {
    if (!hasOfferExtendText(text)) return;
    var page = 1;
    dispatchData(type, urlString, text, page);
    if (isPluginSearchUrl(urlString)) {
      scheduleMemoryScan(text, urlString, page);
    }
  }

  console.log('=== [1688-MAIN] 请求拦截器启动 ===', location.href);

  function buildHookedFetch(targetFetch) {
    return function () {
      var args = arguments;
      var url = args[0];
      var urlString = typeof url === 'string' ? url : url && url.url ? url.url : '';
      var hitPlugin = isPluginSearchUrl(urlString);
      var hitMtop = isMtopUrl(urlString);

      if (hitPlugin) {
        console.log('[1688-MAIN] 命中 fetch 目标请求:', urlString.slice(0, 160));
      }

      var p = targetFetch.apply(this, args);

      if (hitPlugin) {
        p.then(function (response) {
          try {
            response.clone().text().then(function (text) {
              console.log('[1688-MAIN] fetch 原始响应长度:', text.length);
              handleInterceptText('fetch', urlString, text);
            }).catch(function (e) {
              console.log('[1688-MAIN] fetch 读取失败:', e && e.message);
            });
          } catch (e) {
            console.log('[1688-MAIN] clone 失败:', e && e.message);
          }
        });
      } else if (hitMtop) {
        p.then(function (response) {
          try {
            response.clone().text().then(function (text) {
              if (text.indexOf('deliveryChargeInfo') !== -1 && hasOfferExtendText(text)) {
                console.log('[1688-MAIN] 其他 mtop 含邮费:', urlString.slice(0, 120));
                handleInterceptText('mtop-extra', urlString, text);
              }
            }).catch(function () { /* ignore */ });
          } catch (e) { /* ignore */ }
        });
      }

      return p;
    };
  }

  if (_nativeFetch) {
    window.fetch = buildHookedFetch(_nativeFetch);
    console.log('[1688-MAIN] window.fetch 已 hook (native)');
  }

  try {
    if (typeof window.HookBX$1 !== 'undefined' && window.HookBX$1 && window.HookBX$1.window && typeof window.HookBX$1.window.fetch === 'function') {
      window.HookBX$1.window.fetch = buildHookedFetch(window.HookBX$1.window.fetch.bind(window.HookBX$1.window));
      console.log('[1688-MAIN] HookBX$1.window.fetch 已 hook');
    }
  } catch (e) { /* ignore */ }

  var XHR = window.XMLHttpRequest;
  if (XHR && XHR.prototype) {
    var origOpen = XHR.prototype.open;
    var origSend = XHR.prototype.send;

    XHR.prototype.open = function (method, url) {
      this.__gp_url = url;
      return origOpen.apply(this, arguments);
    };

    XHR.prototype.send = function () {
      var xhr = this;
      var urlString = xhr.__gp_url || '';

      if (isPluginSearchUrl(urlString) || isMtopUrl(urlString)) {
        var prevHandler = xhr.onreadystatechange;
        xhr.onreadystatechange = function () {
          if (xhr.readyState === 4 && xhr.status === 200) {
            try {
              var text = xhr.responseText || '';
              if (isPluginSearchUrl(urlString)) {
                console.log('[1688-MAIN] XHR 原始响应长度:', text.length);
                handleInterceptText('xhr', urlString, text);
              } else if (text.indexOf('deliveryChargeInfo') !== -1 && hasOfferExtendText(text)) {
                console.log('[1688-MAIN] XHR 其他 mtop 含邮费:', urlString.slice(0, 120));
                handleInterceptText('xhr-extra', urlString, text);
              }
            } catch (e) {
              console.log('[1688-MAIN] XHR 处理失败:', e && e.message);
            }
          }
          if (prevHandler) prevHandler.apply(xhr, arguments);
        };
      }

      return origSend.apply(this, arguments);
    };

    console.log('[1688-MAIN] XHR 已 hook');
  }

  // 捕获任意代码路径解析出的含邮费 JSON
  JSON.parse = function (text) {
    var result = _origJsonParse.apply(this, arguments);
    try {
      if (typeof text === 'string' && text.length > 50000 &&
          text.indexOf('deliveryChargeInfo') !== -1 &&
          text.indexOf('offerExtend') !== -1) {
        console.log('[1688-MAIN] JSON.parse 捕获含邮费数据, 长度:', text.length);
        dispatchData('json-parse', '', text);
      }
    } catch (e) { /* ignore */ }
    return result;
  };

  console.log('=== [1688-MAIN] 拦截器就绪 ===');
})();
