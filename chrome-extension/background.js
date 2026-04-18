/**
 * 接收内容脚本请求，在指定延时后关闭对应标签页。
 * 页面不能由 window.close() 可靠关闭时，需通过 tabs API。
 */

const CLOSE_MESSAGE = 'CLOSE_TAB_AFTER_DELAY';

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type !== CLOSE_MESSAGE) {
    return false;
  }

  const tabId = sender.tab?.id;
  if (tabId == null) {
    sendResponse({ ok: false, error: 'no_tab' });
    return false;
  }

  const delayMs = Math.max(0, Number(message.delayMs) || 10_000);

  setTimeout(() => {
    chrome.tabs.remove(tabId).catch(() => {
      // 标签已关闭或无权访问时忽略
    });
  }, delayMs);

  sendResponse({ ok: true, tabId, delayMs });
  return false;
});
