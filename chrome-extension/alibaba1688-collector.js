/**
 * 1688 采集脚本 - TikTok页面版本
 * 运行在 TikTok Shop 商品页，拦截1688插件的API请求
 */

(function () {
  'use strict';

  const MESSAGE_TYPES = {
    SAVE_1688_DATA: 'SAVE_1688_DATA',
    CLOSE_1688_PLUGIN: 'CLOSE_1688_PLUGIN',
    COLLECTION_COMPLETE: 'COLLECTION_COMPLETE',
    CLICK_CLOSE_BUTTON: 'CLICK_CLOSE_BUTTON',
  };

  let isCollecting = false;
  let currentTikTokProductId = null;
  let currentProductId = null;
  let originalFetch = window.fetch;
  let originalXHR = window.XMLHttpRequest;

  const isInIframe = window !== window.top;
  const is1688Domain = window.location.hostname.includes('1688.com');

  // 监听1688插件iframe的创建，并动态注入拦截脚本
  function watchAndInjectToIframe() {
    if (isInIframe || is1688Domain) return; // iframe内不需要监听

    console.log('[1688采集] 开始监听1688插件iframe创建...');

    // 定期检查是否有新的1688 iframe创建
    const checkInterval = setInterval(() => {
      const marketMate = document.getElementById('market-mate-for-1688');
      if (marketMate && marketMate.shadowRoot) {
        const iframe = marketMate.shadowRoot.querySelector('#find-goods-iframe');
        if (iframe && !iframe.dataset.injected) {
          console.log('[1688采集] 检测到1688 iframe创建:', iframe.src);
          iframe.dataset.injected = 'true';
          
          // 获取所有frames，找到1688的frameId
          chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            if (tabs.length > 0) {
              chrome.webNavigation.getAllFrames({ tabId: tabs[0].id }, (frames) => {
                if (frames) {
                  frames.forEach((frame) => {
                    if (frame.url && frame.url.includes('1688.com')) {
                      console.log('[1688采集] 找到1688 frame, frameId:', frame.frameId);
                      
                      // 向iframe注入拦截脚本
                      chrome.scripting.executeScript({
                        target: { tabId: tabs[0].id, frameIds: [frame.frameId] },
                        files: ['alibaba1688-collector.js'],
                      }).then(() => {
                        console.log('[1688采集] 成功注入拦截脚本到iframe');
                        
                        // 注入成功后，立即发送采集状态到iframe
                        setTimeout(() => {
                          if (iframe && iframe.contentWindow) {
                            iframe.contentWindow.postMessage({
                              type: 'START_1688_COLLECTION',
                              data: {
                                tiktokProductId: currentTikTokProductId,
                                productId: currentProductId,
                              },
                            }, '*');
                            console.log('[1688采集] 已发送采集状态到iframe');
                          }
                        }, 500); // 等待脚本初始化完成
                      }).catch((e) => {
                        console.log('[1688采集] 注入失败:', e);
                      });
                    }
                  });
                }
              });
            }
          });
        }
      }
    }, 1000);

    // 30秒后停止检查
    setTimeout(() => {
      clearInterval(checkInterval);
      console.log('[1688采集] 停止监听iframe创建');
    }, 30000);

    console.log('[1688采集] 定时检查已启动');
  }

  function parse1688Data(responseData) {
    if (!responseData || !responseData.data || !responseData.data.offerExtend) {
      return [];
    }

    const offerExtend = responseData.data.offerExtend;
    const offerMember = responseData.data.offerMember || {};
    const products = [];

    for (const [offerId, extendData] of Object.entries(offerExtend)) {
      const saleStats = extendData.saleStatsModel || {};
      const shopInfo = extendData.shopInfoModel || {};
      const images = extendData.images || [];

      const product = {
        offerId: offerId,
        memberId: offerMember[offerId] || '',
        title: extendData.title || '',
        images: images,
        mainImage: images[0] || '',
        last30DaysSales: saleStats.last30DaysSales || '',
        totalSales: saleStats.totalSales || '',
        last30DaysDropShippingSales: saleStats.last30DaysDropShippingSales || '',
        goodRates: saleStats.goodRates || 0,
        repurchaseRate: saleStats.repurchaseRate || '',
        collectionRate24h: saleStats.collectionRate24h || '',
        earliestListingTime: saleStats.earliestListingTime || '',
        latestUpdateTime: saleStats.latestUpdateTime || '',
        freeReturnIn7d: shopInfo.freeReturnIn7d || '',
        tpYear: shopInfo.tpYear || 0,
        consignmentSales30d: shopInfo.consignmentSales30d || '',
        shiliType: shopInfo.shiliType || '',
        supportWaybill: (shopInfo.surportWaybill || []).map(w => w.name).join(','),
      };

      products.push(product);
    }

    return products;
  }

  function interceptFetch() {
    console.log('[1688采集] 开始拦截Fetch请求');
    console.log('[1688采集] 当前域名:', window.location.hostname);
    console.log('[1688采集] 当前URL:', window.location.href);
    console.log('[1688采集] window.fetch 类型:', typeof window.fetch);
    
    const originalFetch = window.fetch;
    
    window.fetch = async function(...args) {
      const url = args[0];
      const urlString = typeof url === 'string' ? url : (url && url.url ? url.url : '');
      
      console.log('[1688采集] 📡 Fetch 请求:', urlString.substring(0, 200));
      
      const startTime = Date.now();
      const response = await originalFetch.apply(this, args);
      const duration = Date.now() - startTime;
      
      console.log('[1688采集] ✅ 响应状态:', response.status, `(${duration}ms)`);
      
      if (urlString && urlString.includes('mtop.1688.pc.plugin.imagesearch.plugin.search')) {
        console.log('[1688采集] 🎯 拦截到1688插件请求');
        console.log('[1688采集] isCollecting:', isCollecting);
        
        if (isCollecting) {
          try {
            const clonedResponse = response.clone();
            const data = await clonedResponse.json();
            
            if (data && data.data && data.data.offerExtend) {
              const products = parse1688Data(data);

              console.log('[1688采集] 解析到商品数据, 数量:', products.length);

              chrome.runtime.sendMessage({
                type: MESSAGE_TYPES.SAVE_1688_DATA,
                data: {
                  tiktokProductId: currentTikTokProductId,
                  productId: currentProductId,
                  products: products,
                  timestamp: Date.now(),
                },
              }, (saveResponse) => {
                if (chrome.runtime.lastError) {
                  console.error('[1688采集] 发送数据失败:', chrome.runtime.lastError);
                } else if (saveResponse && saveResponse.success) {
                  console.log('[1688采集] 数据保存成功，1秒后关闭插件');

                  setTimeout(() => {
                    const marketMate = document.getElementById('market-mate-for-1688');
                    if (marketMate && marketMate.shadowRoot) {
                      const iframe = marketMate.shadowRoot.querySelector('#find-goods-iframe');
                      if (iframe && iframe.contentWindow) {
                        iframe.contentWindow.postMessage({ type: 'CLOSE_1688_PLUGIN' }, '*');
                        console.log('[1688采集] 已发送关闭指令到iframe');
                      } else {
                        console.error('[1688采集] 未找到iframe');
                      }
                    } else {
                      console.error('[1688采集] 未找到1688插件容器');
                    }
                  }, 1000);
                }
              });
            } else {
              console.log('[1688采集] 响应数据格式不匹配:', JSON.stringify(data).substring(0, 200));
            }
          } catch (e) {
            console.error('[1688采集] 解析响应失败:', e);
          }
        } else {
          console.log('[1688采集] ️ 拦截到请求但isCollecting=false，跳过处理');
        }
      }

      return response;
    };
    
    console.log('[1688采集] Fetch拦截器已安装');
  }

  function interceptXHR() {
    console.log('[1688采集] 开始拦截XHR请求');
    
    const origOpen = originalXHR.prototype.open;
    const origSend = originalXHR.prototype.send;

    originalXHR.prototype.open = function (method, url) {
      this._url = url;
      return origOpen.apply(this, arguments);
    };

    originalXHR.prototype.send = function () {
      const xhr = this;

      if (xhr._url && xhr._url.includes('mtop.1688.pc.plugin.imagesearch.plugin.search')) {
        console.log('[1688采集] ✅ XHR拦截到1688请求');
        console.log('[1688采集] isCollecting:', isCollecting);
        console.log('[1688采集] URL:', xhr._url.substring(0, 150));
        
        const origOnReadyStateChange = xhr.onreadystatechange;

        xhr.onreadystatechange = function () {
          if (xhr.readyState === 4 && xhr.status === 200) {
            if (isCollecting) {
              try {
                const data = JSON.parse(xhr.responseText);

                if (data && data.data && data.data.offerExtend) {
                  const products = parse1688Data(data);

                  console.log('[1688采集] XHR解析到商品数据, 数量:', products.length);

                  chrome.runtime.sendMessage({
                    type: MESSAGE_TYPES.SAVE_1688_DATA,
                    data: {
                      tiktokProductId: currentTikTokProductId,
                      productId: currentProductId,
                      products: products,
                      timestamp: Date.now(),
                    },
                  }, (saveResponse) => {
                    if (chrome.runtime.lastError) {
                      console.error('[1688采集] 发送数据失败:', chrome.runtime.lastError);
                    } else if (saveResponse && saveResponse.success) {
                      console.log('[1688采集] XHR数据保存成功，1秒后关闭插件');

                      setTimeout(() => {
                        const marketMate = document.getElementById('market-mate-for-1688');
                        if (marketMate && marketMate.shadowRoot) {
                          const iframe = marketMate.shadowRoot.querySelector('#find-goods-iframe');
                          if (iframe && iframe.contentWindow) {
                            iframe.contentWindow.postMessage({ type: 'CLOSE_1688_PLUGIN' }, '*');
                            console.log('[1688采集] 已发送关闭指令到iframe');
                          } else {
                            console.error('[1688采集] 未找到iframe');
                          }
                        } else {
                          console.error('[1688采集] 未找到1688插件容器');
                        }
                      }, 1000);
                    }
                  });
                } else {
                  console.log('[1688采集] XHR响应数据格式不匹配:', JSON.stringify(data).substring(0, 200));
                }
              } catch (e) {
                console.error('[1688采集] XHR解析响应失败:', e);
              }
            } else {
              console.log('[1688采集] ️ XHR拦截到请求但isCollecting=false，跳过处理');
            }
          }

          if (origOnReadyStateChange) {
            origOnReadyStateChange.apply(xhr, arguments);
          }
        };
      }

      return origSend.apply(this, arguments);
    };
    
    console.log('[1688采集] XHR拦截器已安装');
  }

  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'START_1688_COLLECTION') {
      isCollecting = true;
      currentTikTokProductId = message.data.tiktokProductId;
      currentProductId = message.data.productId;
      console.log('[1688采集] 开始采集, TikTok商品ID:', currentTikTokProductId, '商品表ID:', currentProductId);

      if (is1688Domain) {
        console.log('[1688采集] 当前在1688 iframe内，直接设置采集状态');
      } else {
        console.log('[1688采集] 当前在TikTok页面，通过postMessage通知iframe');
        const marketMate = document.getElementById('market-mate-for-1688');
        if (marketMate && marketMate.shadowRoot) {
          const iframe = marketMate.shadowRoot.querySelector('#find-goods-iframe');
          if (iframe && iframe.contentWindow) {
            iframe.contentWindow.postMessage({
              type: 'START_1688_COLLECTION',
              data: {
                tiktokProductId: currentTikTokProductId,
                productId: currentProductId,
              },
            }, '*');
            console.log('[1688采集] 已发送采集状态到iframe');
          }
        }
      }

      sendResponse({ success: true });
    } else if (message.type === 'STOP_1688_COLLECTION') {
      isCollecting = false;
      currentTikTokProductId = null;
      currentProductId = null;
      console.log('[1688采集] 停止采集');
      sendResponse({ success: true });
    }
    return true;
  });

  if (is1688Domain) {
    console.log('[1688采集] 运行在1688 iframe内，启动请求拦截');
    interceptFetch();
    interceptXHR();
    
    window.addEventListener('message', (event) => {
      console.log('[1688采集-iframe] 收到 message 事件:', event.data);
      
      if (event.data && event.data.type === 'CLOSE_1688_PLUGIN') {
        console.log('[1688采集] 收到 postMessage 关闭指令');
        console.log('[1688采集] 当前域名:', window.location.hostname);
        console.log('[1688采集] 当前URL:', window.location.href);
        
        function clickCloseButton() {
          const closeBtns = document.querySelectorAll('[class*="close-icon"]');
          console.log('[1688采集] 查找关闭按钮，找到数量:', closeBtns.length);
          
          if (closeBtns && closeBtns.length > 0) {
            console.log(`[1688采集] 找到 ${closeBtns.length} 个关闭按钮，全部点击`);
            closeBtns.forEach((btn, index) => {
              console.log(`[1688采集] 点击第 ${index + 1} 个关闭按钮`);
              console.log('[1688采集] 按钮元素:', btn);
              btn.click();
            });
            return true;
          }
          return false;
        }

        if (!clickCloseButton()) {
          console.log('[1688采集] 未找到关闭按钮，500ms后重试');
          setTimeout(() => {
            if (!clickCloseButton()) {
              console.log('[1688采集] 重试失败，1s后再次重试');
              setTimeout(() => {
                if (!clickCloseButton()) {
                  console.error('[1688采集] 三次尝试后仍未找到关闭按钮');
                }
              }, 1000);
            }
          }, 500);
        }


        // 测试：拦截当前 iframe 内的 window.fetch 和 XHR 请求
        console.log('[1688采集] 开始测试 iframe 内请求拦截...');
        
        if (window.fetch) {
          const originalFetch = window.fetch;
          window.fetch = async function(...args) {
            const url = args[0];
            const urlString = typeof url === 'string' ? url : (url && url.url ? url.url : '');
            console.log('[1688采集-测试] 📡 iframe内拦截到 Fetch 请求:', urlString.substring(0, 300));
            
            const response = await originalFetch.apply(this, args);
            
            const clonedResponse = response.clone();
            clonedResponse.json().then(data => {
              console.log('[1688采集-测试] 📦 iframe内 Fetch 响应数据:', JSON.stringify(data).substring(0, 500));
            }).catch(e => {
              console.log('[1688采集-测试] iframe内 Fetch 响应不是JSON格式');
            });
            
            return response;
          };
          console.log('[1688采集-测试] iframe 内 window.fetch 拦截器已安装');
        }
        
        if (window.XMLHttpRequest) {
          const OriginalXHR = window.XMLHttpRequest;
          const origOpen = OriginalXHR.prototype.open;
          const origSend = OriginalXHR.prototype.send;
          
          OriginalXHR.prototype.open = function(method, url) {
            this._url = url;
            return origOpen.apply(this, arguments);
          };
          
          OriginalXHR.prototype.send = function() {
            const xhr = this;
            console.log('[1688采集-测试] 📡 iframe内拦截到 XHR 请求:', this._url ? this._url.substring(0, 300) : 'unknown');
            
            const origOnReadyStateChange = xhr.onreadystatechange;
            xhr.onreadystatechange = function() {
              if (xhr.readyState === 4 && xhr.status === 200) {
                console.log('[1688采集-测试] 📦 iframe内 XHR 响应数据:', xhr.responseText.substring(0, 500));
              }
              if (origOnReadyStateChange) {
                origOnReadyStateChange.apply(xhr, arguments);
              }
            };
            
            return origSend.apply(this, arguments);
          };
          console.log('[1688采集-测试] iframe 内 XMLHttpRequest 拦截器已安装');
        }
        
      } else if (event.data && event.data.type === 'START_1688_COLLECTION') {
        isCollecting = true;
        currentTikTokProductId = event.data.data.tiktokProductId;
        currentProductId = event.data.data.productId;
        console.log('[1688采集] 通过postMessage收到采集状态, TikTok商品ID:', currentTikTokProductId, '商品表ID:', currentProductId);
      }
    });
  } else {
    console.log('[1688采集] 运行在TikTok页面，等待采集指令');
    // 监听1688插件iframe的创建，并动态注入拦截脚本
    watchAndInjectToIframe();
  }
})();
