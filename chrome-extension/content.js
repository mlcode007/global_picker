/**
 * 打开商品页后等待 10 秒，按文案「集此商品」查找 span 并点击。
 * 以下情况不点击「集此商品」，仅轮询/定时刷新：
 * - 标题含 Security Check
 * - 页面出现 ERP 未登录弹窗
 * 点击后会延迟检测：若仍出现上述情况（或点完后弹出 ERP 未登录），则不关闭标签页，按 tries/定时刷新重试（此时无法同步 ERP）。
 * 仅在连续检测确认无上述阻塞时，才通知后台延时关页。
 */

(function () {
  'use strict';

  const WAIT_BEFORE_CLICK_MS = 10_000;
  const RETRY_MS = 300;
  const MAX_TRIES = 20;
  const REFRESH_DELAY_MS = 5_000;
  const CLOSE_DELAY_MS = 10_000;
  /** 点击采集后等待弹窗/页面反应，再判断是否关页（多段轮询防慢弹窗） */
  const POST_CLICK_VERIFY_STEP_MS = 500;
  const POST_CLICK_VERIFY_STEPS = 5;

  const CLOSE_MESSAGE = 'CLOSE_TAB_AFTER_DELAY';

  let done = false;
  /** 已对「集此商品」点过一次，在整页刷新前不再重复点击 */
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

  /** 不应采集、也不应结束关页流程（验证页 / ERP 未登录） */
  function shouldBlockCollectClick() {
    return isSecurityCheckPage() || isErpLoginPromptOpen();
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

  /**
   * 点击采集后：若出现验证页/ERP 未登录，则不能同步 ERP，不关页，走刷新节奏。
   * 否则多段延迟后确认关页。
   */
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
      type: CLOSE_MESSAGE,
      delayMs: CLOSE_DELAY_MS,
    });
  }

  function tick() {
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

    const el = findTargetSpan();
    if (el) {
      hasClickedCollect = true;
      performClick(el);
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

  setTimeout(tick, WAIT_BEFORE_CLICK_MS);
})();
