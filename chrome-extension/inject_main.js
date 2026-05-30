/**
 * 1688 请求拦截器 —— MAIN 世界版本
 *
 * 通过 manifest 的 content_scripts (world: "MAIN", run_at: "document_start") 注入，
 * 由 Chrome 保证在每个匹配的 frame（含动态创建的 air.1688.com iframe）中、
 * 早于页面自身脚本执行，且不受页面 CSP 限制。
 *
 * 关键：1688 内部会把原生 fetch 存进 HookBX$1.window.fetch 后再调用，
 * 只要我们在它保存引用之前（document_start 最先执行）替换 window.fetch，
 * 它保存到的就是我们 hook 过的版本；同时也直接覆盖已存在的 HookBX$1。
 *
 * 拦截到目标响应后，通过 CustomEvent 把数据（JSON 字符串）派发给 ISOLATED 世界，
 * 由 alibaba1688-collector.js 接收并上报后台。
 */

(function () {
  'use strict';

  // 防止重复安装（同一 frame 可能被多次注入）
  if (window.__GP_1688_HOOK_INSTALLED__) {
    return;
  }
  window.__GP_1688_HOOK_INSTALLED__ = true;

  var TARGET_API = 'mtop.1688.pc.plugin.imagesearch.plugin.search';

  function isTargetUrl(urlString) {
    if (!urlString) return false;
    return (
      urlString.indexOf(TARGET_API) !== -1 ||
      (urlString.indexOf('imagesearch') !== -1 && urlString.indexOf('plugin') !== -1)
    );
  }

  function dispatchData(type, url, data) {
    try {
      // 用 JSON 字符串跨 world 传递，避免 MAIN/ISOLATED 之间对象引用不可读的问题
      document.dispatchEvent(
        new CustomEvent('__1688_intercept_data', {
          detail: { type: type, url: url, json: JSON.stringify(data) },
        })
      );
    } catch (e) {
      console.log('[1688-MAIN] 派发数据失败:', e && e.message);
    }
  }

  console.log('=== [1688-MAIN] 请求拦截器启动 ===', location.href);

  // ===== 拦截 Fetch =====
  function buildHookedFetch(targetFetch) {
    return function (/* ...args */) {
      var args = arguments;
      var url = args[0];
      var urlString = typeof url === 'string' ? url : url && url.url ? url.url : '';
      var hit = isTargetUrl(urlString);

      if (hit) {
        console.log('[1688-MAIN] 命中 fetch 目标请求:', urlString);
      }

      var p = targetFetch.apply(this, args);

      if (hit) {
        p.then(function (response) {
          try {
            var cloned = response.clone();
            cloned
              .json()
              .then(function (data) {
                console.log('[1688-MAIN] fetch 响应解析成功');
                if (data && data.data) {
                  if (data.data.offerExtend) {
                    console.log('[1688-MAIN] 商品数量(offerExtend):', Object.keys(data.data.offerExtend).length);
                    console.log('[1688-MAIN] offerExtend 数据:', JSON.stringify(data.data.offerExtend, null, 2));
                  }
                  if (data.data.offerList && Array.isArray(data.data.offerList)) {
                    console.log('[1688-MAIN] 商品数量(offerList):', data.data.offerList.length);
                    console.log('[1688-MAIN] offerList 数据:', JSON.stringify(data.data.offerList, null, 2));
                  }
                }
                dispatchData('fetch', urlString, data);
              })
              .catch(function (e) {
                console.log('[1688-MAIN] fetch 响应非 JSON:', e && e.message);
              });
          } catch (e) {
            console.log('[1688-MAIN] clone 响应失败:', e && e.message);
          }
        });
      }

      return p;
    };
  }

  // 1) 覆盖 window.fetch（最先执行，1688 之后保存到的就是这个 hook）
  if (typeof window.fetch === 'function') {
    window.fetch = buildHookedFetch(window.fetch.bind(window));
    console.log('[1688-MAIN] window.fetch 已 hook');
  }

  // 2) 若 HookBX$1 已存在（极少数情况），直接覆盖其 fetch
  try {
    if (typeof window.HookBX$1 !== 'undefined' && window.HookBX$1 && window.HookBX$1.window && typeof window.HookBX$1.window.fetch === 'function') {
      window.HookBX$1.window.fetch = buildHookedFetch(window.HookBX$1.window.fetch.bind(window.HookBX$1.window));
      console.log('[1688-MAIN] HookBX$1.window.fetch 已 hook');
    }
  } catch (e) {
    /* ignore */
  }

  // ===== 拦截 XHR =====
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

      if (isTargetUrl(urlString)) {
        console.log('[1688-MAIN] 命中 XHR 目标请求:', urlString);
        var prevHandler = xhr.onreadystatechange;
        xhr.onreadystatechange = function () {
          if (xhr.readyState === 4 && xhr.status === 200) {
            try {
              var data = JSON.parse(xhr.responseText);
              console.log('[1688-MAIN] XHR 响应解析成功');
              if (data && data.data && data.data.offerExtend) {
                console.log('[1688-MAIN] 商品数量:', Object.keys(data.data.offerExtend).length);
              }
              dispatchData('xhr', urlString, data);
            } catch (e) {
              console.log('[1688-MAIN] XHR 响应解析失败:', e && e.message);
            }
          }
          if (prevHandler) {
            prevHandler.apply(xhr, arguments);
          }
        };
      }

      return origSend.apply(this, arguments);
    };

    console.log('[1688-MAIN] XHR 已 hook');
  }

  console.log('=== [1688-MAIN] 拦截器就绪 ===');
})();
