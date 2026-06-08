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
    
    // Ant Design 表格选中后，行会有 ant-table-row-selected 类
    // 先尝试从所有行中查找被选中的
    const rows = document.querySelectorAll('tr[data-product-id], tr[data-id]');
    rows.forEach((row) => {
      const id = row.getAttribute('data-product-id') || row.getAttribute('data-id');
      if (!id) return;
      
      // 检查该行是否被选中
      const isSelected = row.classList.contains('ant-table-row-selected') ||
                         row.classList.contains('selected') ||
                         row.querySelector('.ant-checkbox-checked') !== null ||
                         row.querySelector('input[type="checkbox"]:checked') !== null;
      
      if (isSelected) {
        ids.push(id);
      }
    });
    
    // Fallback: 查找所有选中的 checkbox
    if (ids.length === 0) {
      const checkboxes = document.querySelectorAll('input[type="checkbox"]:checked, .ant-checkbox-checked input, .el-checkbox__input.is-checked input');
      checkboxes.forEach((cb) => {
        const row = cb.closest('tr[data-product-id], tr[data-id]') || 
                    cb.closest('tr') || 
                    cb.closest('.ant-table-row');
        if (row) {
          const id = row.getAttribute('data-product-id') || row.getAttribute('data-id');
          if (id && !ids.includes(id)) ids.push(id);
        }
      });
    }
    
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
    const imageEl = row.querySelector('.product-image-wrapper img');
    const tiktokProductId = row.getAttribute('data-tiktok-product-id') || productId;
    const crawlTaskId = row.getAttribute('data-crawl-task-id') || '';
    const crawlStatus = row.getAttribute('data-crawl-status') || '';

    return {
      id: productId,
      tiktokProductId: tiktokProductId,
      crawlTaskId: crawlTaskId,
      crawlStatus: crawlStatus,
      title: titleEl ? titleEl.textContent.trim() : '',
      image: imageEl ? imageEl.src : '',
    };
  }

  /**
   * 判断商品是否"数据完整"（标题图片都不是占位/空）
   */
  function isProductDataComplete(productInfo) {
    if (!productInfo) return false;
    const titleEmpty = !productInfo.title || productInfo.title === '' ||
                       productInfo.title.includes('待采集') ||
                       productInfo.title.includes('(待采集)');
    const imageEmpty = !productInfo.image || productInfo.image === '' ||
                       productInfo.image.includes('placeholder') ||
                       productInfo.image.includes('default') ||
                       productInfo.image.includes('no-image');
    return !titleEmpty && !imageEmpty;
  }

  /**
   * 判断商品是否需要先执行批量采集
   * 规则：只要标题或图片为空/占位 → 需要采集（不管 crawl_status 是什么）
   * 因为 crawl_status=done 但前端没刷新完整数据的情况，也需要再采集一次
   */
  function needsCollection(productInfo) {
    if (!productInfo) return false;
    // 标题/图片完整 → 已采集，直接采集1688
    if (isProductDataComplete(productInfo)) return false;
    // 缺数据 → 需要采集
    return true;
  }

  /**
   * 获取登录 token
   */
  function getAuthToken() {
    try { return localStorage.getItem('gp_token'); } catch (e) { return null; }
  }

  /**
   * 触发商品批量采集任务
   */
  async function triggerCollection(productInfo) {
    const token = getAuthToken();
    if (!token) throw new Error('未登录，无法触发采集');
    
    if (!productInfo.crawlTaskId) {
      throw new Error('商品无 crawl_task_id，请先在前台点击"采集"按钮创建任务');
    }
    
    const response = await fetch(`/api/v1/tasks/${productInfo.crawlTaskId}/retry`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) throw new Error(`触发采集失败: HTTP ${response.status}`);
    
    const data = await response.json();
    console.log('[1688采集] 触发采集成功:', data);
    return data;
  }

  /**
   * 点击前端"批量采集"按钮触发批量采集
   * 复用前端的完整轮询、刷新、错误处理逻辑
   * 返回 true 表示成功点击，false 表示按钮未找到或已禁用
   */
  function clickFrontendBatchCrawlButton() {
    console.log('[1688采集] 查找前端"批量采集"按钮…');
    
    // Ant Design 按钮 + 文本匹配
    const allButtons = document.querySelectorAll('button.ant-btn');
    for (const btn of allButtons) {
      const text = btn.textContent.trim();
      // 排除其他按钮（"批量删除"、"批量导入"等）
      if (text === '批量采集' || (text.includes('批量采集') && !text.includes('删除') && !text.includes('导入'))) {
        if (btn.disabled || btn.classList.contains('ant-btn-disabled')) {
          console.warn('[1688采集] "批量采集"按钮被禁用');
          return false;
        }
        console.log('[1688采集] 找到"批量采集"按钮，模拟点击');
        btn.click();
        return true;
      }
    }
    
    // Fallback: 文本搜索
    const buttonsByText = document.querySelectorAll('button');
    for (const btn of buttonsByText) {
      if (btn.textContent.trim() === '批量采集') {
        if (btn.disabled || btn.classList.contains('ant-btn-disabled')) {
          console.warn('[1688采集] "批量采集"按钮被禁用');
          return false;
        }
        btn.click();
        return true;
      }
    }
    
    console.warn('[1688采集] 未找到"批量采集"按钮');
    return false;
  }

  /**
   * 检测前端是否正在执行批量采集（通过观察按钮的 loading 状态）
   * 返回 Promise，在批量采集完成后 resolve
   */
  function waitFrontendBatchCrawlDone(maxWaitMs = 300000) {
    return new Promise((resolve, reject) => {
      const startTime = Date.now();
      let wasLoading = false;
      
      const check = () => {
        // 查找"批量采集"按钮
        const allButtons = document.querySelectorAll('button.ant-btn');
        let batchBtn = null;
        for (const btn of allButtons) {
          const text = btn.textContent.trim();
          if (text === '批量采集' || (text.includes('批量采集') && !text.includes('删除') && !text.includes('导入'))) {
            batchBtn = btn;
            break;
          }
        }
        
        const isLoading = batchBtn && (
          batchBtn.classList.contains('ant-btn-loading') || 
          batchBtn.querySelector('.ant-btn-loading-icon') !== null
        );
        
        if (isLoading) {
          wasLoading = true;
          // 批量采集中，继续等待
          if (Date.now() - startTime > maxWaitMs) {
            reject(new Error('前端批量采集超时（5分钟）'));
            return;
          }
          setTimeout(check, 1000);
        } else {
          if (wasLoading) {
            // 已经进入 loading 状态，又退出了，说明批量采集已完成
            console.log('[1688采集] 前端批量采集已完成');
            resolve();
          } else {
            // 还没进入 loading 状态，可能是按钮被点了但还没开始
            if (Date.now() - startTime > 30000) {
              // 30秒都没进入 loading 状态，认为可能失败了
              reject(new Error('前端批量采集未启动（30秒未进入 loading 状态）'));
              return;
            }
            setTimeout(check, 500);
          }
        }
      };
      
      check();
    });
  }

  /**
   * 轮询等待采集完成
   */
  async function waitForCollectionDone(crawlTaskId, productId, maxWaitMs = 300000) {
    const token = getAuthToken();
    if (!token || !crawlTaskId) return null;
    
    const startTime = Date.now();
    const pollInterval = 2000;
    
    while (Date.now() - startTime < maxWaitMs) {
      try {
        const response = await fetch(`/api/v1/tasks/${crawlTaskId}`, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        });
        
        if (response.ok) {
          const result = await response.json();
          const task = result.data || result;
          console.log(`[1688采集] 轮询任务 #${crawlTaskId} 状态: ${task.status}`);
          updateProductLog(productId, `采集状态: ${task.status}`, 'info');
          
          if (task.status === 'done') return task;
          if (task.status === 'failed' || task.status === 'error') {
            throw new Error(`采集失败: ${task.error_msg || '未知错误'}`);
          }
        }
      } catch (e) {
        console.warn('[1688采集] 轮询异常:', e.message);
      }
      
      await new Promise(resolve => setTimeout(resolve, pollInterval));
    }
    
    throw new Error('采集超时（5分钟）');
  }

  /**
   * 采集完成后刷新商品信息
   */
  async function refreshProductInfo(productInfo) {
    const token = getAuthToken();
    if (!token) return productInfo;
    
    try {
      const response = await fetch(`/api/v1/products/${productInfo.id}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      
      if (response.ok) {
        const result = await response.json();
        const fresh = result.data || result;
        console.log('[1688采集] 刷新商品信息成功:', fresh);
        return {
          id: productInfo.id,
          tiktokProductId: fresh.tiktok_product_id || productInfo.tiktokProductId,
          crawlTaskId: fresh.crawl_task_id || productInfo.crawlTaskId,
          title: fresh.title || fresh.product_title || productInfo.title,
          image: fresh.main_image_url || fresh.image_url || productInfo.image,
        };
      }
    } catch (e) {
      console.warn('[1688采集] 刷新商品信息失败:', e.message);
    }
    
    return productInfo;
  }

  // 记录当前正在比价的归属商品，写入 chrome.storage.local(collector/后台入库时读取)。
  // 每次触发都会覆盖，确保入库归属的是“当前任务”的商品，而非残留的旧值。
  // sync-inject 运行在主站页面(localhost/globalpicker)，可直接读取前端写入的 localStorage。
  // 前端「每笔最多入库」会把值写到 localStorage.gp_1688_sync_limit。
  function readSyncLimitFromPage() {
    try {
      const raw = localStorage.getItem('gp_1688_sync_limit');
      const n = parseInt(raw, 10);
      if (Number.isFinite(n) && n >= 1 && n <= 30) return n;
    } catch (e) { /* ignore */ }
    return 5; // 默认
  }

  let lastSetContextId = null;
  function set1688Context(productId, tiktokProductId) {
    if (!productId) return;
    if (String(productId) === String(lastSetContextId)) return; // 同一商品不重复写入
    lastSetContextId = productId;

    const syncLimit = readSyncLimitFromPage();
    const ctx = {
      productId: productId,
      tiktokProductId: tiktokProductId || productId,
      syncLimit: syncLimit,
      ts: Date.now(),
    };
    try {
      chrome.storage.local.set({ gp_1688_context: ctx, gp_1688_sync_limit: syncLimit });
    } catch (e) { /* ignore */ }
    chrome.runtime.sendMessage({
      type: 'START_1688_COLLECTION',
      data: { tiktokProductId: ctx.tiktokProductId, productId: ctx.productId, syncLimit: syncLimit },
    }, () => { void chrome.runtime.lastError; });
    console.log('[1688采集] 锁定归属商品 productId=' + productId + ', tiktokProductId=' + ctx.tiktokProductId + ', syncLimit=' + syncLimit);
  }

  function trigger1688ImageSearch(productInfo) {
    const row = document.querySelector(`tr[data-product-id="${productInfo.id}"]`);
    if (!row) {
      console.error('[1688采集] 找不到商品行:', productInfo.id);
      return;
    }

    // 触发比价前先锁定归属商品（覆盖任何残留上下文）
    set1688Context(productInfo.id, productInfo.tiktokProductId);

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

        // 主动通知后台：插件即将在页内打开 iframe，请枚举注入拦截脚本（含延时重试）
        // 注意：丝滑流程走页内 iframe 比价，不再新开 1688 标签页（OPEN_1688_TAB）
        chrome.runtime.sendMessage({
          type: 'INJECT_1688_NOW',
          data: {
            tiktokProductId: productInfo.tiktokProductId,
            productId: productInfo.id,
            syncLimit: readSyncLimitFromPage(),
          },
        }, () => { void chrome.runtime.lastError; });
      } else {
        console.error('[1688采集] 未找到同款比价按钮');
        updateProductLog(productInfo.id, '未找到同款比价按钮', 'error');
      }
    }, 500);
  }

  async function processNextProduct() {
    if (!isCollecting1688 || currentIndex >= selectedProducts.length) {
      stopCollection();
      return;
    }

    const product = selectedProducts[currentIndex];
    console.log(`[1688采集] 处理第 ${currentIndex + 1}/${selectedProducts.length} 个商品:`, product);

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

    // ── 步骤 1: 检查商品是否已采集，未采集则先触发批量采集 ──
    if (needsCollection(product)) {
      console.log('[1688采集] 商品未采集，先执行批量采集:', product);
      updateProductLog(product.id, '检测到商品未采集，先执行批量采集…', 'warning');
      
      // 找到未采集的商品，记录其原始索引
      const uncollectedIndices = [];
      for (let i = 0; i < selectedProducts.length; i++) {
        if (needsCollection(selectedProducts[i])) {
          uncollectedIndices.push(i);
        }
      }
      
      console.log(`[1688采集] 共 ${uncollectedIndices.length} 个未采集商品`);
      updateProductLog(product.id, `共 ${uncollectedIndices.length} 个未采集商品，先批量采集…`, 'warning');
      
      // 点击前端"批量采集"按钮
      const clicked = clickFrontendBatchCrawlButton();
      if (!clicked) {
        updateProductLog(product.id, '⚠ 未找到前端"批量采集"按钮，尝试单独触发采集', 'error');
        
        // Fallback: 单独触发采集
        try {
          if (!product.crawlTaskId) {
            updateProductLog(product.id, '⚠ 商品无 crawl_task_id，跳过', 'error');
            currentIndex++;
            setTimeout(() => processNextProduct(), 1000);
            return;
          }
          
          await triggerCollection(product);
          await waitForCollectionDone(product.crawlTaskId, product.id);
          const refreshedInfo = await refreshProductInfo(product);
          if (refreshedInfo.title) {
            selectedProducts[currentIndex] = refreshedInfo;
            product.title = refreshedInfo.title;
            product.image = refreshedInfo.image;
            product.crawlTaskId = refreshedInfo.crawlTaskId;
          }
        } catch (err) {
          updateProductLog(product.id, `采集失败: ${err.message}`, 'error');
          currentIndex++;
          setTimeout(() => processNextProduct(), 2000);
          return;
        }
      } else {
        // 等待前端批量采集完成
        try {
          updateProductLog(product.id, '等待前端批量采集完成…', 'info');
          await waitFrontendBatchCrawlDone();
          updateProductLog('__all__', '前端批量采集已完成', 'success');
          
          // 批量采集完成后，重新拉取所有未采集商品的信息
          for (const idx of uncollectedIndices) {
            const p = selectedProducts[idx];
            const refreshed = await refreshProductInfo(p);
            if (refreshed.title) {
              selectedProducts[idx] = refreshed;
              console.log(`[1688采集] 商品 ${p.id} 信息已刷新: ${refreshed.title}`);
              updateProductLog(p.id, `商品信息已刷新: ${refreshed.title.substring(0, 30)}`, 'success');
            }
          }
          
          // 重新读取当前商品的最新信息
          const currentProduct = selectedProducts[currentIndex];
          Object.assign(product, currentProduct);
        } catch (err) {
          updateProductLog('__all__', `前端批量采集异常: ${err.message}`, 'error');
          // 继续执行1688采集
        }
      }
    } else {
      console.log('[1688采集] 商品已采集，跳过批量采集');
      updateProductLog(product.id, '商品已采集', 'info');
    }

    // ── 步骤 2: 执行1688采集 ──
    trigger1688ImageSearch(product);

    updateProductLog(product.id, '已打开1688比价', 'success');
    
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
    // 不再用 p.image 过滤（未采集商品的图片可能是空的占位图）
    // 让所有选中的商品都通过，在 processNextProduct 中再判断是否需要先采集
    selectedProducts = getSelectedProductIds()
      .map(id => getProductInfo(id))
      .filter(p => p); // 只过滤掉完全找不到行元素的商品

    if (selectedProducts.length === 0) {
      alert('请先选择要采集的商品');
      return;
    }

    selectedProducts.forEach(p => {
      const row = document.querySelector(`tr[data-product-id="${p.id}"], tr[data-id="${p.id}"]`);
      if (row) {
        const logContainer = row.querySelector('.gp-1688-product-log');
        if (logContainer) logContainer.remove();
      }
    });

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
    const existingButtons = document.getElementById('gp-1688-buttons');
    const toolbar = document.querySelector('.toolbar, .action-bar, .btn-group, [class*="toolbar"], [class*="action-bar"]');
    
    if (!toolbar) return;
    
    if (existingButtons) {
      if (toolbar.contains(existingButtons)) {
        return;
      }
      existingButtons.remove();
    }

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
    let injected = false;
    
    const observer = new MutationObserver((mutations, obs) => {
      const toolbar = document.querySelector('.toolbar, .action-bar, .btn-group, [class*="toolbar"], [class*="action-bar"]');
      if (toolbar) {
        inject1688Buttons();
        injected = true;
      }
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true,
    });

    // 定期检查按钮是否存在，如果不存在则重新注入
    const checkInterval = setInterval(() => {
      const toolbar = document.querySelector('.toolbar, .action-bar, .btn-group, [class*="toolbar"], [class*="action-bar"]');
      const buttons = document.getElementById('gp-1688-buttons');
      
      if (toolbar && !buttons) {
        inject1688Buttons();
        injected = true;
      }
    }, 1000);

    // 初始注入
    setTimeout(() => {
      inject1688Buttons();
      injected = true;
    }, 500);

    // 5分钟后停止定期检查以节省资源
    setTimeout(() => {
      clearInterval(checkInterval);
      observer.disconnect();
    }, 300000);
  }

  if (window.location.pathname.includes('/product') || window.location.pathname.includes('/goods')) {
    waitForToolbar();
  }

  // ── 持续把前端写入的 localStorage.gp_1688_sync_limit 镜像到 chrome.storage.local ──
  // 这样无论触发时机/去重如何，后台入库时都能读到「每笔最多入库」的最新值。
  let lastMirroredSyncLimit = null;
  function mirror1688SyncLimit() {
    try {
      const raw = localStorage.getItem('gp_1688_sync_limit');
      const n = parseInt(raw, 10);
      const val = (Number.isFinite(n) && n >= 1 && n <= 30) ? n : null;
      if (val != null && val !== lastMirroredSyncLimit) {
        lastMirroredSyncLimit = val;
        chrome.storage.local.set({ gp_1688_sync_limit: val }, () => { void chrome.runtime.lastError; });
        console.log('[1688采集] 已镜像 syncLimit 到扩展存储:', val);
      }
    } catch (e) { /* ignore */ }
  }
  mirror1688SyncLimit();
  setInterval(mirror1688SyncLimit, 1500);
  window.addEventListener('storage', (e) => {
    if (e.key === 'gp_1688_sync_limit') mirror1688SyncLimit();
  });

  // ── 手动触发兜底：手动 hover 某个商品图片即锁定该商品为归属，捕获“同款比价”点击二次确认 ──
  // 覆盖用户不走「1688采集」按钮、而是手动逐个 hover 图片点同款比价的情况。
  // 要触发同款比价必须先 hover 商品图片，所以在图片 hover 时直接同步 productId 最可靠。
  let lastHoveredProduct = null;

  document.addEventListener('mouseover', (e) => {
    const target = e.target;
    if (!target || !target.closest) return;
    const row = target.closest('[data-product-id]');
    if (!row) return;
    const id = row.getAttribute('data-product-id');
    if (!id) return;
    lastHoveredProduct = {
      productId: id,
      tiktokProductId: row.getAttribute('data-tiktok-product-id') || id,
    };
    // 悬停到商品图片即锁定归属（批量采集进行中时不抢占，避免打断队列）
    if (!isCollecting1688 && target.closest('img')) {
      set1688Context(lastHoveredProduct.productId, lastHoveredProduct.tiktokProductId);
    }
  }, true);

  // 用 composedPath 判断是否点中“同款比价”插件（可穿透 shadow DOM；按钮容器 id 是随机生成的，不能写死）
  function pathHitsCompare(e) {
    const path = (e.composedPath && e.composedPath()) || [];
    for (const node of path) {
      if (!node || node.nodeType !== 1) continue;
      const id = (node.id || '');
      if (id.indexOf('market-mate-for-1688') === 0) return true;
      const cls = (typeof node.className === 'string') ? node.className : '';
      if (/compare|bijia|image-?search|find-?goods/i.test(cls)) return true;
      const t = (node.textContent || '').trim();
      if (t && t.length <= 30 && t.indexOf('同款比价') !== -1) return true;
    }
    return false;
  }

  function handleCompareTrigger(e) {
    // ── 诊断：始终打印点击路径，便于定位按钮结构（穿透 shadow）──
    try {
      const path = (e.composedPath && e.composedPath()) || [];
      const desc = path.slice(0, 12).map(n => {
        if (!n || n.nodeType !== 1) return String(n && n.toString ? n.toString() : n);
        const id = n.id ? '#' + n.id : '';
        const cls = (typeof n.className === 'string' && n.className) ? '.' + n.className.trim().split(/\s+/).join('.') : '';
        const txt = (n.textContent || '').trim().slice(0, 10);
        return (n.tagName || '').toLowerCase() + id + cls + (txt ? '{' + txt + '}' : '');
      });
      console.log('[1688调试] PATH>>>', e.type, desc);
    } catch (err) { /* ignore */ }

    if (!pathHitsCompare(e)) return;

    const ctx = lastHoveredProduct;
    if (!ctx || !ctx.productId) {
      // alert('[1688调试] 点中同款比价插件，但未捕获到归属商品（请先把鼠标移到某个商品图片上）lastHovered=' + JSON.stringify(ctx));
      console.warn('[1688调试] 点中同款比价插件，但未捕获到归属商品（请先把鼠标移到某个商品图片上）lastHovered=', ctx);
      return;
    }
    lastSetContextId = null; // 调试期间绕过去重，确保每次都写入
    set1688Context(ctx.productId, ctx.tiktokProductId);
    chrome.storage.local.get('gp_1688_context', (r) => {
      // alert('[1688调试] 点中同款比价 ...');
      console.log('[1688调试] 点中同款比价, 当前 productId=' + ctx.productId +
            ', tiktokProductId=' + ctx.tiktokProductId +
            ', 已写入缓存 gp_1688_context=', r && r.gp_1688_context);
    });
  }

  // mousedown 最早触发、最不易被插件吞掉；click 兜底
  document.addEventListener('mousedown', handleCompareTrigger, true);
  document.addEventListener('click', handleCompareTrigger, true);

  // 接收 background.js 发来的 1688 入库成功通知，转发给网页
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'GP_1688_SAVED' && message.data && message.data.productId) {
      console.log('[1688采集] 收到入库成功通知，productId:', message.data.productId);
      window.postMessage({ source: 'gp-extension', type: 'GP_1688_SAVED', productId: message.data.productId }, '*');
    }
  });

  console.log('[同步注入] 已启动，监听登录状态变化');
})();
