/**
 * 同步注入脚本
 * 运行在 Global Picker 网页上，监听 localStorage 变化
 * 当用户登录/退出时，通知插件后台服务
 */

(function () {
  'use strict';

  const TOKEN_KEY = 'gp_token';
  const USER_KEY = 'gp_user';

  let lastToken = localStorage.getItem(TOKEN_KEY);

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

  console.log('[同步注入] 已启动，监听登录状态变化');
})();
