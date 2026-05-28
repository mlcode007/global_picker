/**
 * 后台服务
 * 负责：登录状态自动同步、配额管理、API 通信、消息处理
 */

const CONFIG = {
  apiBaseUrl: 'https://www.globalpicker.com/api/v1',
  dailyCollectionLimit: 10000,
  authCheckInterval: 5 * 60 * 1000,
  requestTimeout: 10000,
  retryCount: 3,
  retryDelay: 1000,
};

const STORAGE_KEYS = {
  TOKEN: 'gp_token',
  USER: 'gp_user',
  POINTS: 'gp_points',
  TODAY_COUNT: 'gp_today_count',
  QUOTA_DATE: 'gp_quota_date',
  LAST_SYNC: 'gp_last_sync',
};

const MESSAGE_TYPES = {
  CLOSE_TAB: 'CLOSE_TAB_AFTER_DELAY',
  CHECK_AUTH: 'CHECK_AUTH',
  CHECK_QUOTA: 'CHECK_QUOTA',
  CHECK_ALL: 'CHECK_ALL',
  RECORD_COLLECTION: 'RECORD_COLLECTION',
  SYNC_AUTH: 'SYNC_AUTH',
  GET_STATUS: 'GET_STATUS',
  GP_AUTH_CHANGED: 'GP_AUTH_CHANGED',
  SAVE_1688_DATA: 'SAVE_1688_DATA',
  CLOSE_1688_TAB: 'CLOSE_1688_TAB',
  START_1688_COLLECTION: 'START_1688_COLLECTION',
  STOP_1688_COLLECTION: 'STOP_1688_COLLECTION',
  OPEN_1688_TAB: 'OPEN_1688_TAB',
  CLOSE_1688_PLUGIN: 'CLOSE_1688_PLUGIN',
  CLICK_CLOSE_BUTTON: 'CLICK_CLOSE_BUTTON',
};

// ── 日志工具 ──
const Logger = {
  level: 'info',
  levels: { debug: 0, info: 1, warn: 2, error: 3 },

  _log(level, ...args) {
    if (this.levels[level] >= this.levels[this.level]) {
      console[level === 'error' ? 'error' : level === 'warn' ? 'warn' : 'log']('[采集助手]', ...args);
    }
  },

  debug(...args) { this._log('debug', ...args); },
  info(...args) { this._log('info', ...args); },
  warn(...args) { this._log('warn', ...args); },
  error(...args) { this._log('error', ...args); },
};

// ── 存储管理 ──
const StorageManager = {
  async get(key, defaultValue = null) {
    try {
      const result = await chrome.storage.local.get(key);
      return result[key] !== undefined ? result[key] : defaultValue;
    } catch (e) {
      Logger.error('读取存储失败:', key, e);
      return defaultValue;
    }
  },

  async set(key, value) {
    try {
      await chrome.storage.local.set({ [key]: value });
    } catch (e) {
      Logger.error('写入存储失败:', key, e);
    }
  },

  async remove(key) {
    try {
      await chrome.storage.local.remove(key);
    } catch (e) {
      Logger.error('删除存储失败:', key, e);
    }
  },

  async getTodayCount() {
    const today = new Date().toISOString().slice(0, 10);
    const storedDate = await this.get(STORAGE_KEYS.QUOTA_DATE, '');
    if (storedDate !== today) {
      await this.set(STORAGE_KEYS.TODAY_COUNT, 0);
      await this.set(STORAGE_KEYS.QUOTA_DATE, today);
      return 0;
    }
    return await this.get(STORAGE_KEYS.TODAY_COUNT, 0);
  },

  async incrementTodayCount() {
    const count = await this.getTodayCount();
    await this.set(STORAGE_KEYS.TODAY_COUNT, count + 1);
    return count + 1;
  },
};

// ── API 客户端 ──
const ApiClient = {
  async request(method, path, data = null, token = null) {
    const url = `${CONFIG.apiBaseUrl}${path}`;
    const headers = { 'Content-Type': 'application/json' };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), CONFIG.requestTimeout);

    let lastError;
    for (let i = 0; i < CONFIG.retryCount; i++) {
      try {
        const response = await fetch(url, {
          method,
          headers,
          body: data ? JSON.stringify(data) : null,
          signal: controller.signal,
        });
        clearTimeout(timeoutId);

        const result = await response.json();

        if (!response.ok) {
          const errorDetail = result.detail || result.message || '请求失败';
          throw { status: response.status, detail: errorDetail, data: result };
        }

        return { success: true, data: result.data };
      } catch (e) {
        lastError = e;
        if (e.name === 'AbortError') {
          Logger.error(`请求超时: ${method} ${path}`);
          return { success: false, error: { code: 'TIMEOUT', message: '请求超时' } };
        }
        if (i < CONFIG.retryCount - 1) {
          await new Promise(r => setTimeout(r, CONFIG.retryDelay * (i + 1)));
        }
      }
    }

    Logger.error(`API 请求失败: ${method} ${path}`, lastError);
    return {
      success: false,
      error: {
        code: lastError.status === 401 ? 'AUTH_FAILED' : 'NETWORK_ERROR',
        message: lastError.detail || lastError.message || '网络请求失败',
      },
    };
  },

  async verifyAuth(token) {
    return this.request('POST', '/auth/verify', null, token);
  },

  async getQuotaStatus(token) {
    return this.request('GET', '/quota/status', null, token);
  },

  async recordCollection(token, productUrl = null, productId = null) {
    return this.request('POST', '/quota/record', { product_url: productUrl, product_id: productId }, token);
  },
};

// ── 验证器 ──
const Validator = {
  async checkAuth() {
    const token = await StorageManager.get(STORAGE_KEYS.TOKEN);
    if (!token) {
      return { success: false, error: { code: 'AUTH_NOT_LOGGED_IN', message: '未登录' } };
    }

    const result = await ApiClient.verifyAuth(token);
    if (!result.success) {
      if (result.error.code === 'AUTH_FAILED') {
        await StorageManager.remove(STORAGE_KEYS.TOKEN);
        await StorageManager.remove(STORAGE_KEYS.USER);
        await StorageManager.remove(STORAGE_KEYS.POINTS);
      }
      return result;
    }

    if (result.data?.user) {
      await StorageManager.set(STORAGE_KEYS.USER, result.data.user);
    }
    if (result.data?.points !== undefined) {
      await StorageManager.set(STORAGE_KEYS.POINTS, result.data.points);
    }
    await StorageManager.set(STORAGE_KEYS.LAST_SYNC, Date.now());

    return { success: true, data: result.data };
  },

  async checkQuota() {
    const token = await StorageManager.get(STORAGE_KEYS.TOKEN);
    if (!token) {
      return { success: false, error: { code: 'AUTH_NOT_LOGGED_IN', message: '未登录' } };
    }

    const todayCount = await StorageManager.getTodayCount();
    const dailyLimit = CONFIG.dailyCollectionLimit;

    if (todayCount >= dailyLimit) {
      return {
        success: false,
        error: {
          code: 'QUOTA_EXCEEDED',
          message: `今日采集配额已用完（${todayCount}/${dailyLimit}）`,
        },
      };
    }

    return {
      success: true,
      data: { todayCount, dailyLimit, remaining: dailyLimit - todayCount },
    };
  },

  async checkAll() {
    const authResult = await this.checkAuth();
    if (!authResult.success) {
      return authResult;
    }

    const quotaResult = await this.checkQuota();
    if (!quotaResult.success) {
      return quotaResult;
    }

    return {
      success: true,
      data: {
        user: authResult.data?.user,
        points: authResult.data?.points,
        ...quotaResult.data,
      },
    };
  },
};

// ── 后台服务 ──
const BackgroundService = {
  initialized: false,

  async init() {
    if (this.initialized) return;

    Logger.info('初始化后台服务...');

    this.setupMessageListener();
    this.setupTabUpdateListener();
    this.startPeriodicTasks();

    await this.autoSyncAuth();

    this.initialized = true;
    Logger.info('后台服务初始化完成');
  },

  async autoSyncAuth() {
    try {
      const existingToken = await StorageManager.get(STORAGE_KEYS.TOKEN);
      if (existingToken) {
        Logger.info('已有 token，尝试验证...');
        const result = await Validator.checkAuth();
        if (result.success) {
          Logger.info('登录状态有效');
          return;
        }
        Logger.info('token 已过期，尝试从网页同步...');
      }

      await this.syncFromWebPage();
    } catch (e) {
      Logger.debug('自动同步登录失败:', e);
    }
  },

  async syncFromWebPage() {
    try {
      const tabs = await chrome.tabs.query({ url: ['http://localhost:5173/*', 'http://localhost:8000/*', 'http://www.globalpicker.com/*', 'https://www.globalpicker.com/*', 'http://47.238.72.198/*'] });
      if (tabs.length === 0) {
        Logger.debug('未找到 Global Picker 页面');
        return false;
      }

      for (const tab of tabs) {
        try {
          const results = await chrome.scripting.executeScript({
            target: { tabId: tab.id },
            func: () => {
              const token = localStorage.getItem('gp_token');
              const userRaw = localStorage.getItem('gp_user');
              let user = null;
              try { user = userRaw ? JSON.parse(userRaw) : null; } catch (e) { /* ignore */ }
              return { token, user };
            },
          });
          if (results?.[0]?.result?.token) {
            const { token, user } = results[0].result;
            Logger.info('从网页同步到 token');
            await StorageManager.set(STORAGE_KEYS.TOKEN, token);
            if (user) {
              await StorageManager.set(STORAGE_KEYS.USER, user);
            }
            const authResult = await Validator.checkAuth();
            return authResult.success;
          }
        } catch (e) {
          Logger.debug('从标签页读取 token 失败:', tab.id);
        }
      }

      Logger.info('网页未登录，清除插件登录状态');
      await StorageManager.remove(STORAGE_KEYS.TOKEN);
      await StorageManager.remove(STORAGE_KEYS.USER);
      await StorageManager.remove(STORAGE_KEYS.POINTS);
      return false;
    } catch (e) {
      Logger.error('从网页同步失败:', e);
      return false;
    }
  },

  async handleAuthChanged(eventType, token, user) {
    Logger.info('收到网页登录状态变化:', eventType);

    if (eventType === 'login' || eventType === 'token_changed') {
      if (token) {
        await StorageManager.set(STORAGE_KEYS.TOKEN, token);
        if (user) {
          await StorageManager.set(STORAGE_KEYS.USER, user);
        }
        const authResult = await Validator.checkAuth();
        if (authResult.success) {
          Logger.info('登录状态同步成功');
        } else {
          Logger.warn('登录状态验证失败:', authResult.error);
        }
      }
    } else if (eventType === 'logout') {
      Logger.info('网页已退出，同步清除插件登录状态');
      await StorageManager.remove(STORAGE_KEYS.TOKEN);
      await StorageManager.remove(STORAGE_KEYS.USER);
      await StorageManager.remove(STORAGE_KEYS.POINTS);
    }
  },

  setupMessageListener() {
    chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
      Logger.debug('收到消息:', message.type);

      switch (message.type) {
        case MESSAGE_TYPES.CLOSE_TAB:
          this.handleCloseTab(message, sender, sendResponse);
          return false;

        case MESSAGE_TYPES.CHECK_AUTH:
          Validator.checkAuth().then(sendResponse);
          return true;

        case MESSAGE_TYPES.CHECK_QUOTA:
          Validator.checkQuota().then(sendResponse);
          return true;

        case MESSAGE_TYPES.CHECK_ALL:
          Validator.checkAll().then(sendResponse);
          return true;

        case MESSAGE_TYPES.RECORD_COLLECTION:
          this.handleRecordCollection(message, sendResponse);
          return true;

        case MESSAGE_TYPES.SYNC_AUTH:
          this.handleSyncAuth(sender, sendResponse);
          return true;

        case MESSAGE_TYPES.GET_STATUS:
          this.handleGetStatus(sendResponse);
          return true;

        case MESSAGE_TYPES.GP_AUTH_CHANGED:
          this.handleAuthChanged(message.data.event, message.data.token, message.data.user);
          sendResponse({ success: true });
          return false;

        case MESSAGE_TYPES.SAVE_1688_DATA:
          this.handleSave1688Data(message, sendResponse);
          return true;

        case MESSAGE_TYPES.CLOSE_1688_TAB:
          this.handleClose1688Tab(sender, sendResponse);
          return false;

        case MESSAGE_TYPES.OPEN_1688_TAB:
          this.handleOpen1688Tab(message, sendResponse);
          return false;

        case MESSAGE_TYPES.CLOSE_1688_PLUGIN:
          this.handleClose1688Plugin(sender, sendResponse);
          return true;

        default:
          return false;
      }
    });
  },

  setupTabUpdateListener() {
    chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
      if (changeInfo.status === 'complete' && tab.url &&
          (tab.url.startsWith('http://localhost:5173') || tab.url.startsWith('http://localhost:8000') || tab.url.startsWith('http://www.globalpicker.com') || tab.url.startsWith('https://www.globalpicker.com') || tab.url.startsWith('http://47.238.72.198'))) {
        Logger.info('检测到 Global Picker 页面加载完成，尝试同步登录状态');
        setTimeout(() => this.syncFromWebPage(), 2000);
      }
    });

    chrome.tabs.onRemoved.addListener((tabId) => {
      const token = StorageManager.get(STORAGE_KEYS.TOKEN);
      if (token) {
        Logger.info('Global Picker 页面关闭，尝试验证 token 有效性');
        setTimeout(() => Validator.checkAuth(), 1000);
      }
    });
  },

  handleCloseTab(message, sender) {
    const tabId = sender.tab?.id;
    if (tabId == null) return;

    const delayMs = Math.max(0, Number(message.delayMs) || 10_000);

    setTimeout(() => {
      chrome.tabs.remove(tabId).catch(() => {});
    }, delayMs);
  },

  async handleRecordCollection(message, sendResponse) {
    try {
      const token = await StorageManager.get(STORAGE_KEYS.TOKEN);
      if (!token) {
        sendResponse({ success: false, error: { code: 'AUTH_NOT_LOGGED_IN', message: '未登录' } });
        return;
      }

      const quotaResult = await Validator.checkQuota();
      if (!quotaResult.success) {
        sendResponse(quotaResult);
        return;
      }

      const result = await ApiClient.recordCollection(token);
      if (result.success) {
        await StorageManager.incrementTodayCount();
      }

      sendResponse(result);
    } catch (e) {
      Logger.error('记录采集失败:', e);
      sendResponse({ success: false, error: { code: 'RECORD_ERROR', message: '记录采集失败' } });
    }
  },

  async handleSyncAuth(sender, sendResponse) {
    try {
      const success = await this.syncFromWebPage();
      if (success) {
        sendResponse({ success: true });
      } else {
        sendResponse({ success: false, error: { code: 'NOT_LOGGED_IN', message: '网页未登录，请先在 <a href="https://www.globalpicker.com" target="_blank" style="color:inherit;text-decoration:underline;">Global Picker</a> 平台登录' } });
      }
    } catch (e) {
      Logger.error('同步登录状态失败:', e);
      sendResponse({ success: false, error: { code: 'SYNC_ERROR', message: '同步失败: ' + e.message } });
    }
  },

  async handleGetStatus(sendResponse) {
    try {
      const token = await StorageManager.get(STORAGE_KEYS.TOKEN);
      const user = await StorageManager.get(STORAGE_KEYS.USER);
      const points = await StorageManager.get(STORAGE_KEYS.POINTS);
      const todayCount = await StorageManager.getTodayCount();
      const lastSync = await StorageManager.get(STORAGE_KEYS.LAST_SYNC);

      sendResponse({
        success: true,
        data: {
          isLoggedIn: !!token,
          user: user || null,
          points: points || 0,
          todayCount,
          dailyLimit: CONFIG.dailyCollectionLimit,
          lastSync: lastSync || null,
        },
      });
    } catch (e) {
      Logger.error('获取状态失败:', e);
      sendResponse({ success: false, error: { code: 'STATUS_ERROR', message: '获取状态失败' } });
    }
  },

  async handleSave1688Data(message, sendResponse) {
    try {
      const { tiktokProductId, productId, products } = message.data;

      Logger.info(`收到1688数据: TikTok商品ID=${tiktokProductId}, 商品表ID=${productId}, 商品数量=${products.length}`);

      const token = await StorageManager.get(STORAGE_KEYS.TOKEN);
      if (!token) {
        sendResponse({ success: false, error: { code: 'AUTH_NOT_LOGGED_IN', message: '未登录' } });
        return;
      }

      const url = `${CONFIG.apiBaseUrl}/1688/products/batch`;
      const headers = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      };

      const response = await fetch(url, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          tiktok_product_id: tiktokProductId,
          product_id: productId,
          products: products,
        }),
      });

      const result = await response.json();

      if (!response.ok) {
        Logger.error('1688数据入库失败:', result);
        sendResponse({ success: false, error: { code: 'API_ERROR', message: result.detail || result.message || '入库失败' } });
        return;
      }

      Logger.info('1688数据入库成功');
      sendResponse({ success: true, data: result.data });
    } catch (e) {
      Logger.error('保存1688数据失败:', e);
      sendResponse({ success: false, error: { code: 'SAVE_ERROR', message: '保存失败: ' + e.message } });
    }
  },

  handleClose1688Tab(sender) {
    const tabId = sender.tab?.id;
    if (tabId == null) return;

    chrome.tabs.remove(tabId).catch(() => {});
    Logger.info('关闭1688标签页:', tabId);
  },

  handleOpen1688Tab(message, sendResponse) {
    const { url, tiktokProductId, productId } = message.data;

    chrome.tabs.create({ url, active: true }, (tab) => {
      Logger.info('打开1688标签页:', tab.id, 'TikTok商品ID:', tiktokProductId, '商品表ID:', productId);

      setTimeout(() => {
        chrome.tabs.sendMessage(tab.id, {
          type: 'START_1688_COLLECTION',
          data: { 
            tiktokProductId: tiktokProductId,
            productId: productId,
          },
        }, (response) => {
          if (chrome.runtime.lastError) {
            Logger.error('发送采集指令失败:', chrome.runtime.lastError);
          }
        });
      }, 2000);
    });
  },

  async handleClose1688Plugin(sender, sendResponse) {
    const tabId = sender.tab?.id;
    if (!tabId) {
      sendResponse({ success: false, error: '无法获取标签页ID' });
      return;
    }

    Logger.info('收到关闭1688插件请求，标签页:', tabId);

    try {
      const frames = await chrome.webNavigation.getAllFrames({ tabId });
      Logger.info('找到 frames:', frames?.length || 0);

      if (frames && frames.length > 0) {
        for (const frame of frames) {
          if (frame.url && frame.url.includes('1688.com')) {
            Logger.info('向1688 frame发送关闭指令, frameId:', frame.frameId);
            chrome.tabs.sendMessage(tabId, { type: 'CLOSE_1688_PLUGIN' }, { frameId: frame.frameId }, (response) => {
              if (chrome.runtime.lastError) {
                Logger.error('发送关闭指令失败:', chrome.runtime.lastError);
              } else {
                Logger.info('关闭指令已发送, 响应:', response);
              }
            });
            break;
          }
        }
      }

      sendResponse({ success: true });
    } catch (e) {
      Logger.error('关闭1688插件失败:', e);
      sendResponse({ success: false, error: e.message });
    }
  },

  startPeriodicTasks() {
    setInterval(async () => {
      const token = await StorageManager.get(STORAGE_KEYS.TOKEN);
      if (token) {
        Logger.info('定时检查登录状态...');
        const result = await Validator.checkAuth();
        if (!result.success) {
          Logger.info('登录状态失效，尝试从网页同步...');
          await this.syncFromWebPage();
        }
      } else {
        await this.syncFromWebPage();
      }
    }, CONFIG.authCheckInterval);
  },
};

// ── 启动 ──
BackgroundService.init();
