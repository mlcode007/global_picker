/**
 * 内容脚本
 * 负责页面交互、采集按钮点击、页面状态检测
 * 在每次点击采集按钮前进行登录状态和配额校验
 */

(function () {
  'use strict';

  const WAIT_BEFORE_CLICK_MS = 10_000;
  const RETRY_MS = 300;
  const MAX_TRIES = 20;
  const REFRESH_DELAY_MS = 5_000;
  const CLOSE_DELAY_MS = 10_000;
  const POST_CLICK_VERIFY_STEP_MS = 500;
  const POST_CLICK_VERIFY_STEPS = 5;

  const MESSAGE_TYPES = {
    CLOSE_TAB: 'CLOSE_TAB_AFTER_DELAY',
    CHECK_ALL: 'CHECK_ALL',
    RECORD_COLLECTION: 'RECORD_COLLECTION',
    SYNC_AUTH: 'SYNC_AUTH',
  };

  let done = false;
  let hasClickedCollect = false;
  let tries = 0;
  let reloadScheduled = false;

  function isSecurityCheckPage() {
    const t = (document.title || '').trim();
    return /security check/i.test(t);
  }

  function isErpLoginPromptOpen() {
    const raw = document.body?.innerText || '';
    if (!raw) return false;
    if (raw.includes('您还未登录ERP软件')) return true;
    if (raw.includes('未登录ERP') && raw.includes('立即登录')) return true;
    if (raw.includes('请先登录') && raw.includes('ERP') && raw.includes('立即登录')) return true;
    return false;
  }

  function shouldBlockCollectClick() {
    return isSecurityCheckPage() || isErpLoginPromptOpen();
  }

  function syncAuth() {
    return new Promise((resolve) => {
      chrome.runtime.sendMessage({ type: MESSAGE_TYPES.SYNC_AUTH }, (response) => {
        if (chrome.runtime.lastError) {
          console.error('[采集助手] 同步登录状态失败:', chrome.runtime.lastError);
          resolve({
            success: false,
            error: { code: 'SYNC_ERROR', message: '同步登录状态失败' },
          });
          return;
        }
        resolve(response);
      });
    });
  }

  function checkAuthAndQuota() {
    return new Promise((resolve) => {
      chrome.runtime.sendMessage({ type: MESSAGE_TYPES.CHECK_ALL }, (response) => {
        if (chrome.runtime.lastError) {
          console.error('[采集助手] 检查登录状态和配额失败:', chrome.runtime.lastError);
          resolve({
            success: false,
            error: { code: 'COMMUNICATION_ERROR', message: '与后台通信失败' },
          });
          return;
        }
        resolve(response);
      });
    });
  }

  function recordCollection() {
    return new Promise((resolve) => {
      chrome.runtime.sendMessage({ type: MESSAGE_TYPES.RECORD_COLLECTION }, (response) => {
        if (chrome.runtime.lastError) {
          console.error('[采集助手] 记录采集失败:', chrome.runtime.lastError);
          resolve({
            success: false,
            error: { code: 'RECORD_ERROR', message: '记录采集失败' },
          });
          return;
        }
        resolve(response);
      });
    });
  }

  function findTargetSpan() {
    return [...document.querySelectorAll('span')].find((s) => s.textContent.includes('集此商品'));
  }

  function performClick(el) {
    try {
      el.scrollIntoView({ block: 'center', inline: 'center', behavior: 'instant' });
    } catch {
      /* ignore */
    }
    if (typeof el.click === 'function') {
      el.click();
    }
  }

  function scheduleReload() {
    if (reloadScheduled) return;
    reloadScheduled = true;
    setTimeout(() => {
      window.location.reload();
    }, REFRESH_DELAY_MS);
  }

  function showNotification(message, type = 'error') {
    const notification = document.createElement('div');
    notification.style.cssText = `
      position: fixed;
      top: 20px;
      left: 50%;
      transform: translateX(-50%);
      padding: 12px 24px;
      border-radius: 8px;
      font-size: 14px;
      font-weight: 500;
      z-index: 10000;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      animation: slideDown 0.3s ease;
      max-width: 90%;
      text-align: center;
    `;

    const colors = {
      error: { bg: '#fee2e2', text: '#991b1b', border: '#fca5a5' },
      warning: { bg: '#fef3c7', text: '#92400e', border: '#fcd34d' },
      success: { bg: '#d1fae5', text: '#065f46', border: '#6ee7b7' },
      info: { bg: '#dbeafe', text: '#1e40af', border: '#93c5fd' },
    };

    const color = colors[type] || colors.info;
    notification.style.backgroundColor = color.bg;
    notification.style.color = color.text;
    notification.style.border = `1px solid ${color.border}`;
    notification.innerHTML = message;

    document.body.appendChild(notification);

    setTimeout(() => {
      notification.style.animation = 'slideUp 0.3s ease';
      setTimeout(() => notification.remove(), 300);
    }, 5000);
  }

  function verifyAfterClick(step) {
    if (done) return;
    const s = step == null ? 0 : step;

    if (shouldBlockCollectClick()) {
      tries = 0;
      setTimeout(tick, RETRY_MS);
      return;
    }

    if (s < POST_CLICK_VERIFY_STEPS - 1) {
      setTimeout(() => verifyAfterClick(s + 1), POST_CLICK_VERIFY_STEP_MS);
      return;
    }

    done = true;
    chrome.runtime.sendMessage({
      type: MESSAGE_TYPES.CLOSE_TAB,
      delayMs: CLOSE_DELAY_MS,
    });
  }

  async function tick() {
    if (done) return;

    if (shouldBlockCollectClick()) {
      tries += 1;
      if (tries >= MAX_TRIES) {
        scheduleReload();
        return;
      }
      setTimeout(tick, RETRY_MS);
      return;
    }

    if (hasClickedCollect) {
      tries += 1;
      if (tries >= MAX_TRIES) {
        scheduleReload();
        return;
      }
      setTimeout(tick, RETRY_MS);
      return;
    }

    const syncResult = await syncAuth();
    if (!syncResult.success) {
      console.log('[采集助手] 同步登录状态失败:', syncResult.error);
      showNotification('未登录 <a href="http://localhost:5173" target="_blank" style="color:inherit;text-decoration:underline;">Global Picker</a> 平台，请先登录', 'error');
      tries += 1;
      if (tries >= MAX_TRIES) {
        scheduleReload();
        return;
      }
      setTimeout(tick, RETRY_MS);
      return;
    }

    const quotaStatus = await checkAuthAndQuota();

    if (!quotaStatus.success) {
      console.log('[采集助手] 校验失败:', quotaStatus.error);

      if (quotaStatus.error.code === 'AUTH_NOT_LOGGED_IN' ||
          quotaStatus.error.code === 'AUTH_TOKEN_EXPIRED' ||
          quotaStatus.error.code === 'AUTH_FAILED') {
        showNotification('未登录 <a href="http://localhost:5173" target="_blank" style="color:inherit;text-decoration:underline;">Global Picker</a> 平台，请先登录', 'error');
      } else if (quotaStatus.error.code === 'POINTS_INSUFFICIENT') {
        showNotification('积分不足，请充值后再试', 'warning');
      } else if (quotaStatus.error.code === 'QUOTA_EXCEEDED') {
        showNotification(quotaStatus.error.message, 'warning');
      } else {
        showNotification('校验失败: ' + quotaStatus.error.message, 'error');
      }

      tries += 1;
      if (tries >= MAX_TRIES) {
        scheduleReload();
        return;
      }
      setTimeout(tick, RETRY_MS);
      return;
    }

    const el = findTargetSpan();
    if (el) {
      const recordResult = await recordCollection();
      if (!recordResult.success) {
        console.error('[采集助手] 记录采集失败:', recordResult.error);
        showNotification('记录采集失败，请稍后重试', 'error');
        tries += 1;
        if (tries >= MAX_TRIES) {
          scheduleReload();
          return;
        }
        setTimeout(tick, RETRY_MS);
        return;
      }

      hasClickedCollect = true;
      performClick(el);
      showNotification('采集成功', 'success');
      setTimeout(() => verifyAfterClick(0), POST_CLICK_VERIFY_STEP_MS);
      return;
    }

    tries += 1;
    if (tries >= MAX_TRIES) {
      scheduleReload();
      return;
    }

    setTimeout(tick, RETRY_MS);
  }

  const style = document.createElement('style');
  style.textContent = `
    @keyframes slideDown {
      from { transform: translate(-50%, -100%); opacity: 0; }
      to { transform: translate(-50%, 0); opacity: 1; }
    }
    @keyframes slideUp {
      from { transform: translate(-50%, 0); opacity: 1; }
      to { transform: translate(-50%, -100%); opacity: 0; }
    }
  `;
  document.head.appendChild(style);

  setTimeout(tick, WAIT_BEFORE_CLICK_MS);
})();
