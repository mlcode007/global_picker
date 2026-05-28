/**
 * 同步注入脚本
 * 运行在 Global Picker 网页上，监听 localStorage 变化
 * 当用户登录/退出时，通知插件后台服务
 * 同时注入1688采集按钮到商品列表页
 */

(function () {
  'use strict';

  const TOKEN_KEY = 'gp_token';
  const USER_KEY = 'gp_user';

  let lastToken = localStorage.getItem(TOKEN_KEY);

  let isCollecting1688 = false;
  let selectedProducts = [];
  let currentIndex = 0;
  let collectionTimer = null;
  let collectionStartTime = null;
  let timerInterval = null;
  let progressToast = null;

  function notifyBackground(eventType) {
    const token = localStorage.getItem(TOKEN_KEY);
    const userRaw = localStorage.getItem(USER_KEY);
    let user = null;
    try {
      user = userRaw ? JSON.parse(userRaw) : null;
    } catch (e) { /* ignore */ }

    chrome.runtime.sendMessage({
      type: 'GP_AUTH_CHANGED',
      data: {
        event: eventType,
        token: token,
        user: user,
      },
    }, () => {
      if (chrome.runtime.lastError) {
        console.debug('[同步注入] 通知后台失败:', chrome.runtime.lastError);
      }
    });
  }

  const originalSetItem = Storage.prototype.setItem;
  Storage.prototype.setItem = function (key, value) {
    originalSetItem.apply(this, arguments);
    if (key === TOKEN_KEY) {
      const oldToken = lastToken;
      lastToken = value;
      if (value && !oldToken) {
        notifyBackground('login');
      } else if (!value && oldToken) {
        notifyBackground('logout');
      } else if (value !== oldToken) {
        notifyBackground('token_changed');
      }
    }
  };

  const originalRemoveItem = Storage.prototype.removeItem;
  Storage.prototype.removeItem = function (key) {
    const oldValue = this.getItem(key);
    originalRemoveItem.apply(this, arguments);
    if (key === TOKEN_KEY && oldValue) {
      lastToken = null;
      notifyBackground('logout');
    }
  };

  const originalClear = Storage.prototype.clear;
  Storage.prototype.clear = function () {
    originalClear.apply(this, arguments);
    if (lastToken) {
      lastToken = null;
      notifyBackground('logout');
    }
  };

  window.addEventListener('storage', (e) => {
    if (e.key === TOKEN_KEY) {
      const oldToken = lastToken;
      lastToken = e.newValue;
      if (e.newValue && !oldToken) {
        notifyBackground('login');
      } else if (!e.newValue && oldToken) {
        notifyBackground('logout');
      } else if (e.newValue !== oldToken) {
        notifyBackground('token_changed');
      }
    }
  });

  function getSelectedProductIds() {
    const ids = [];
    
    const checkboxes = document.querySelectorAll('input[type="checkbox"]:checked, .ant-checkbox-checked input, .el-checkbox__input.is-checked input');
    console.log('[1688采集] 找到选中的checkbox数量:', checkboxes.length);
    
    checkboxes.forEach((cb, index) => {
      const row = cb.closest('tr') || cb.closest('.ant-table-row') || cb.closest('[class*="row"]') || cb.closest('[class*="item"]');
      
      if (row) {
        const id = row.getAttribute('data-product-id');
        console.log(`[1688采集] ID ${index}:`, id);
        if (id) ids.push(id);
      }
    });
    
    console.log('[1688采集] 最终获取到的IDs:', ids);
    return ids;
  }

  function createProgressToast() {
    if (progressToast) {
      progressToast.remove();
    }

    progressToast = document.createElement('div');
    progressToast.id = 'gp-1688-progress-toast';
    progressToast.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      padding: 16px 24px;
      border-radius: 12px;
      font-size: 14px;
      box-shadow: 0 8px 32px rgba(102, 126, 234, 0.4);
      z-index: 999999999;
      min-width: 280px;
      backdrop-filter: blur(10px);
      border: 1px solid rgba(255, 255, 255, 0.2);
      transition: all 0.3s ease;
    `;

    progressToast.innerHTML = `
      <div style="flex: 1; text-align: right;">
        <div id="gp-1688-progress-text" style="font-size: 13px; opacity: 0.9;">正在处理第 1/1 个商品</div>
        <div id="gp-1688-timer-text" style="font-size: 12px; opacity: 0.8; margin-top: 4px;">用时: 00:00</div>
      </div>
    `;

    document.body.appendChild(progressToast);
    console.log('[1688采集] 进度提示框已创建');
  }

  function updateProgressToast(current, total, productId) {
    if (!progressToast) return;

    const progressText = document.getElementById('gp-1688-progress-text');
    if (progressText) {
      progressText.textContent = `TikTok ID: ${productId} (${current}/${total})`;
    }
  }

  function updateTimerText() {
    if (!progressToast || !collectionStartTime) return;

    const elapsed = Math.floor((Date.now() - collectionStartTime) / 1000);
    const minutes = Math.floor(elapsed / 60);
    const seconds = elapsed % 60;
    const timeStr = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;

    const timerText = document.getElementById('gp-1688-timer-text');
    if (timerText) {
      timerText.textContent = `用时: ${timeStr}`;
    }
  }

  function removeProgressToast() {
    if (progressToast) {
      progressToast.style.opacity = '0';
      progressToast.style.transform = 'translateY(-20px)';
      setTimeout(() => {
        if (progressToast) {
          progressToast.remove();
          progressToast = null;
        }
      }, 300);
    }

    if (timerInterval) {
      clearInterval(timerInterval);
      timerInterval = null;
    }

    // 不再删除商品日志，保留采集记录
    // const allLogs = document.querySelectorAll('.gp-1688-product-log');
    // allLogs.forEach(log => log.remove());
  }

  function updateProductLog(productId, message, type) {
    const row = document.querySelector(`tr[data-product-id="${productId}"], tr[data-id="${productId}"]`);
    if (!row) return;

    let logContainer = row.querySelector('.gp-1688-product-log');
    
    if (!logContainer) {
      logContainer = document.createElement('div');
      logContainer.className = 'gp-1688-product-log';
      logContainer.style.cssText = `
        margin-top: 4px;
        font-size: 12px;
        line-height: 1.7;
        font-family: 'Menlo', 'Monaco', monospace;
      `;

      const existingBatch = row.querySelector('.erp-batch-row, .photo-batch-row');
      if (existingBatch) {
        existingBatch.appendChild(logContainer);
      } else {
        let titleContainer = row.querySelector('.product-title, .product-name, td:nth-child(2) a, [class*="title"]')?.closest('td, div');
        
        if (!titleContainer) {
          const cells = row.querySelectorAll('td');
          for (const cell of cells) {
            const hasLink = cell.querySelector('a[href]');
            const hasLongText = cell.textContent.length > 30;
            if (hasLink && hasLongText) {
              titleContainer = cell;
              break;
            }
          }
        }

        if (titleContainer) {
          titleContainer.appendChild(logContainer);
        }
      }
    }

    const colorMap = {
      info: '#666',
      success: '#52c41a',
      warning: '#faad14',
      error: '#f5222d',
      step: '#1890ff',
    };
    const color = colorMap[type] || colorMap.info;
    const iconMap = { info: '•', success: '✓', warning: '⚠', error: '✗', step: '▸' };
    const icon = iconMap[type] || '•';

    const line = document.createElement('div');
    line.style.color = color;
    line.textContent = `${icon} ${message}`;

    logContainer.appendChild(line);
  }

  function getProductInfo(productId) {
    const row = document.querySelector(`tr[data-product-id="${productId}"], tr[data-id="${productId}"]`);
    if (!row) return null;

    const titleEl = row.querySelector('.product-title, .product-name, td:nth-child(2) a');
    const imageEl = row.querySelector('img');
    const tiktokProductId = row.getAttribute('data-tiktok-product-id') || productId;

    return {
      id: productId,
      tiktokProductId: tiktokProductId,
      title: titleEl ? titleEl.textContent.trim() : '',
      image: imageEl ? imageEl.src : '',
    };
  }

  function trigger1688ImageSearch(productInfo) {
    const row = document.querySelector(`tr[data-product-id="${productInfo.id}"]`);
    if (!row) {
      console.error('[1688采集] 找不到商品行:', productInfo.id);
      return;
    }

    const imageEl = row.querySelector('img');
    if (!imageEl) {
      console.error('[1688采集] 找不到商品图片');
      return;
    }

    const rect = imageEl.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;

    const mouseMove = new MouseEvent('mousemove', {
      bubbles: true,
      cancelable: true,
      clientX: centerX,
      clientY: centerY,
      view: window,
    });
    imageEl.dispatchEvent(mouseMove);

    const mouseEnter = new MouseEvent('mouseenter', {
      bubbles: true,
      cancelable: true,
      clientX: centerX,
      clientY: centerY,
      view: window,
    });
    imageEl.dispatchEvent(mouseEnter);

    const mouseOver = new MouseEvent('mouseover', {
      bubbles: true,
      cancelable: true,
      clientX: centerX,
      clientY: centerY,
      view: window,
    });
    imageEl.dispatchEvent(mouseOver);

    setTimeout(() => {
      const allSpans = document.querySelectorAll('span');
      let targetBtn = null;
      
      allSpans.forEach(span => {
        if (!targetBtn && span.textContent.trim() === '同款比价') {
          targetBtn = span;
        }
      });
      
      if (targetBtn) {
        console.log('[1688采集] 找到同款比价按钮，点击');
        updateProductLog(productInfo.id, '点击同款比价按钮', 'success');
        targetBtn.click();
        
        // 通知alibaba1688-collector.js开始采集
        chrome.runtime.sendMessage({
          type: 'START_1688_COLLECTION',
          data: {
            tiktokProductId: productInfo.tiktokProductId,
            productId: productInfo.id,
          },
        }, (response) => {
          if (chrome.runtime.lastError) {
            console.error('[1688采集] 发送START_1688_COLLECTION失败:', chrome.runtime.lastError);
          } else {
            console.log('[1688采集] 已发送START_1688_COLLECTION消息');
          }
        });
      } else {
        console.error('[1688采集] 未找到同款比价按钮');
        updateProductLog(productInfo.id, '未找到同款比价按钮', 'error');
      }
    }, 500);
  }

  function processNextProduct() {
    if (!isCollecting1688 || currentIndex >= selectedProducts.length) {
      stopCollection();
      return;
    }

    const product = selectedProducts[currentIndex];
    console.log(`[1688采集] 处理第 ${currentIndex + 1}/${selectedProducts.length} 个商品:`, product.title);

    collectionStartTime = Date.now();
    updateProgressToast(currentIndex + 1, selectedProducts.length, product.tiktokProductId);
    updateProductLog(product.id, `开始采集 (${currentIndex + 1}/${selectedProducts.length})`, 'step');

    chrome.runtime.sendMessage({
      type: 'UPDATE_1688_STATUS',
      data: {
        status: 'collecting',
        current: currentIndex,
        total: selectedProducts.length,
      },
    });

    trigger1688ImageSearch(product);

    updateProductLog(product.id, '已打开', 'success');
    
    setTimeout(() => {
      console.log('[1688采集] 10秒到了，准备更新日志为"采集完成"，商品ID:', product.id);
      const row = document.querySelector(`tr[data-product-id="${product.id}"], tr[data-id="${product.id}"]`);
      console.log('[1688采集] 找到商品行:', !!row);
      updateProductLog(product.id, '采集完成', 'success');
      
      const marketMate = document.getElementById('market-mate-for-1688');
      if (marketMate && marketMate.shadowRoot) {
        const iframe = marketMate.shadowRoot.querySelector('#find-goods-iframe');
        if (iframe && iframe.contentWindow) {
          iframe.contentWindow.postMessage({ type: 'CLOSE_1688_PLUGIN' }, '*');
        }
      }

      currentIndex++;
      
      setTimeout(() => {
        processNextProduct();
      }, 2000);
    }, 10000);
  }

  function startCollection() {
    selectedProducts = getSelectedProductIds().map(id => getProductInfo(id)).filter(p => p && p.image);

    if (selectedProducts.length === 0) {
      alert('请先选择要采集的商品');
      return;
    }

    isCollecting1688 = true;
    currentIndex = 0;
    collectionStartTime = Date.now();

    const startBtn = document.getElementById('gp-start-1688-btn');
    const stopBtn = document.getElementById('gp-stop-1688-btn');
    if (startBtn) startBtn.style.display = 'none';
    if (stopBtn) stopBtn.style.display = 'inline-block';

    chrome.runtime.sendMessage({
      type: 'UPDATE_1688_STATUS',
      data: {
        status: 'collecting',
        current: 0,
        total: selectedProducts.length,
      },
    });

    createProgressToast();
    timerInterval = setInterval(updateTimerText, 1000);

    console.log(`[1688采集] 开始采集 ${selectedProducts.length} 个商品`);
    processNextProduct();
  }

  function stopCollection() {
    isCollecting1688 = false;
    currentIndex = 0;
    selectedProducts = [];

    const startBtn = document.getElementById('gp-start-1688-btn');
    const stopBtn = document.getElementById('gp-stop-1688-btn');
    if (startBtn) startBtn.style.display = 'inline-block';
    if (stopBtn) stopBtn.style.display = 'none';

    chrome.runtime.sendMessage({
      type: 'UPDATE_1688_STATUS',
      data: {
        status: 'stopped',
        current: 0,
        total: 0,
      },
    });

    removeProgressToast();

    console.log('[1688采集] 停止采集，发送关闭插件指令');

    const marketMate = document.getElementById('market-mate-for-1688');
    
    if (marketMate && marketMate.shadowRoot) {
      const iframe = marketMate.shadowRoot.querySelector('#find-goods-iframe');
      
      if (iframe && iframe.contentWindow) {
        try {
          iframe.contentWindow.postMessage({ type: 'CLOSE_1688_PLUGIN' }, '*');
          console.log('[1688采集] ✅ postMessage 发送成功');
        } catch (e) {
          console.error('[1688采集] ❌ postMessage 发送失败:', e);
        }
      }
    }

    console.log('[1688采集] 停止采集');
  }

  function inject1688Buttons() {
    if (document.getElementById('gp-1688-buttons')) return;

    const toolbar = document.querySelector('.toolbar, .action-bar, .btn-group, [class*="toolbar"], [class*="action-bar"]');
    if (!toolbar) return;

    const container = document.createElement('div');
    container.id = 'gp-1688-buttons';
    container.style.cssText = 'display: inline-flex; gap: 8px; margin-left: 12px;';

    const startBtn = document.createElement('button');
    startBtn.id = 'gp-start-1688-btn';
    startBtn.textContent = '1688采集';
    startBtn.style.cssText = `
      padding: 6px 16px;
      background: linear-gradient(135deg, #ff6a00 0%, #ee0979 100%);
      color: white;
      border: none;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s ease;
    `;
    startBtn.addEventListener('mouseenter', () => {
      startBtn.style.transform = 'translateY(-1px)';
      startBtn.style.boxShadow = '0 4px 12px rgba(238, 9, 121, 0.3)';
    });
    startBtn.addEventListener('mouseleave', () => {
      startBtn.style.transform = 'translateY(0)';
      startBtn.style.boxShadow = 'none';
    });
    startBtn.addEventListener('click', startCollection);

    const stopBtn = document.createElement('button');
    stopBtn.id = 'gp-stop-1688-btn';
    stopBtn.textContent = '关闭1688采集';
    stopBtn.style.cssText = `
      padding: 6px 16px;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      border: none;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s ease;
      display: none;
    `;
    stopBtn.addEventListener('mouseenter', () => {
      stopBtn.style.transform = 'translateY(-1px)';
      stopBtn.style.boxShadow = '0 4px 12px rgba(118, 75, 162, 0.3)';
    });
    stopBtn.addEventListener('mouseleave', () => {
      stopBtn.style.transform = 'translateY(0)';
      stopBtn.style.boxShadow = 'none';
    });
    stopBtn.addEventListener('click', stopCollection);

    container.appendChild(startBtn);
    container.appendChild(stopBtn);
    toolbar.appendChild(container);

    console.log('[1688采集] 按钮已注入');
  }

  function waitForToolbar() {
    const observer = new MutationObserver((mutations, obs) => {
      if (document.querySelector('.toolbar, .action-bar, .btn-group, [class*="toolbar"], [class*="action-bar"]')) {
        inject1688Buttons();
        obs.disconnect();
      }
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true,
    });

    setTimeout(() => {
      inject1688Buttons();
      observer.disconnect();
    }, 3000);
  }

  if (window.location.pathname.includes('/product') || window.location.pathname.includes('/goods')) {
    waitForToolbar();
  }

  console.log('[同步注入] 已启动，监听登录状态变化');
})();
