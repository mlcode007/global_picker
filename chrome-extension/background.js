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

// 应用页面 URL（用于同步登录态 / 推断 API 地址）
const APP_TAB_URLS = [
  'http://localhost:5173/*', 'http://localhost:8000/*',
  'http://globalpicker.com/*', 'https://globalpicker.com/*',
  'http://www.globalpicker.com/*', 'https://www.globalpicker.com/*',
  'http://47.238.72.198/*',
];

// 按登录来源推断后端 API 地址：本地开发走 8000，生产走 globalpicker.com
function resolveApiBase(urlStr) {
  try {
    const u = new URL(urlStr);
    const host = u.hostname;
    if (host === 'localhost' || host === '127.0.0.1') return 'http://localhost:8000/api/v1';
    if (host.endsWith('globalpicker.com')) return 'https://www.globalpicker.com/api/v1';
    return `${u.protocol}//${u.host}/api/v1`;
  } catch (e) {
    return CONFIG.apiBaseUrl;
  }
}

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
  DEBUG_1688_HOOK_HIT: 'DEBUG_1688_HOOK_HIT',
  INJECT_1688_NOW: 'INJECT_1688_NOW',
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
  current1688Context: null,

  async init() {
    if (this.initialized) return;

    console.log('%c[采集助手] BUILD MARKER >>> 1688-HOOK-v3 (webNav+executeScript+frameEnum) <<<', 'color:#fff;background:#ee0979;padding:2px 6px;border-radius:3px;');
    Logger.info('初始化后台服务...');

    this.setupMessageListener();
    this.setupTabUpdateListener();
    this.setup1688FrameInjection();
    this.startPeriodicTasks();

    await this.refreshApiBase();
    await this.autoSyncAuth();

    this.initialized = true;
    Logger.info('后台服务初始化完成');
  },

  // 根据当前打开的应用页面动态设置 API 地址（本地/生产自适应）
  async refreshApiBase() {
    try {
      const tabs = await chrome.tabs.query({ url: APP_TAB_URLS });
      if (tabs && tabs.length) {
        // 优先本地开发页面，避免同时开着生产页时误发到生产
        const localTab = tabs.find(t => /https?:\/\/(localhost|127\.0\.0\.1)/.test(t.url || ''));
        const base = resolveApiBase((localTab || tabs[0]).url);
        if (base !== CONFIG.apiBaseUrl) {
          Logger.info(`API 地址切换为: ${base}`);
        }
        CONFIG.apiBaseUrl = base;
        await StorageManager.set('gp_api_base', base);
      } else {
        const stored = await StorageManager.get('gp_api_base');
        if (stored) CONFIG.apiBaseUrl = stored;
      }
    } catch (e) {
      Logger.debug('刷新 API 地址失败:', e && e.message);
    }
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
      const tabs = await chrome.tabs.query({ url: APP_TAB_URLS });
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

        case MESSAGE_TYPES.START_1688_COLLECTION:
          this.handleStart1688Collection(message, sendResponse);
          return false;

        case 'UPDATE_1688_SYNC_LIMIT':
          this.handleUpdate1688SyncLimit(message, sendResponse);
          return false;

        case MESSAGE_TYPES.STOP_1688_COLLECTION:
          this.current1688Context = null;
          StorageManager.remove('gp_1688_context');
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

        case MESSAGE_TYPES.DEBUG_1688_HOOK_HIT:
          Logger.info(`🎯 [HOOK命中] 拦截到1688请求 type=${message.requestType} count=${message.count} url=${(message.url || '').slice(0, 120)}`);
          sendResponse({ success: true });
          return false;

        case MESSAGE_TYPES.INJECT_1688_NOW:
          // 由网页侧（sync-inject）在打开插件后主动触发，枚举该 tab 注入
          if (sender.tab && sender.tab.id != null) {
            Logger.info('收到 INJECT_1688_NOW，枚举注入 tab=' + sender.tab.id);
            
            // 如果消息中携带了商品信息，更新采集上下文
            if (message.data && (message.data.tiktokProductId != null || message.data.productId != null)) {
              this.current1688Context = {
                tiktokProductId: message.data.tiktokProductId != null ? message.data.tiktokProductId : null,
                productId: message.data.productId != null ? message.data.productId : null,
                ts: Date.now(),
              };
              StorageManager.set('gp_1688_context', this.current1688Context);
              Logger.info(`更新1688采集上下文: TikTok商品ID=${this.current1688Context.tiktokProductId}, 商品表ID=${this.current1688Context.productId}`);
            }
            
            this.inject1688AllFrames(sender.tab.id);
            // 插件 iframe 可能稍后才创建，做几次延时重试
            setTimeout(() => this.inject1688AllFrames(sender.tab.id), 800);
            setTimeout(() => this.inject1688AllFrames(sender.tab.id), 2000);
            setTimeout(() => this.inject1688AllFrames(sender.tab.id), 4000);
          }
          sendResponse({ success: true });
          return false;

        default:
          return false;
      }
    });
  },

  // 主动把拦截脚本注入 air.1688.com 子 frame（等价手动 F12 注入）
  // 声明式 content script 注入到「另一扩展在 Shadow DOM 里动态创建的跨域子frame」不可靠，
  // 这里改由后台监听 webNavigation，拿到 frameId 后用 scripting.executeScript 精准注入。
  inject1688Hook(tabId, frameId) {
    if (tabId == null || frameId == null) return;

    // MAIN 世界：hook fetch/XHR
    chrome.scripting.executeScript({
      target: { tabId, frameIds: [frameId] },
      world: 'MAIN',
      injectImmediately: true,
      files: ['inject_main.js'],
    }).then(() => {
      Logger.info('✅ 已注入 inject_main.js (MAIN) tab=' + tabId + ' frame=' + frameId);
    }).catch((e) => {
      Logger.warn('❌ 注入 inject_main.js 失败 frame=' + frameId + ':', e && e.message);
    });

    // ISOLATED 世界：接收 MAIN 派发的拦截数据（含守卫，重复注入会 no-op）
    chrome.scripting.executeScript({
      target: { tabId, frameIds: [frameId] },
      injectImmediately: true,
      files: ['alibaba1688-collector.js'],
    }).then(() => {
      Logger.info('✅ 已注入 alibaba1688-collector.js (ISOLATED) tab=' + tabId + ' frame=' + frameId);
    }).catch((e) => {
      Logger.warn('❌ 注入 alibaba1688-collector.js 失败 frame=' + frameId + ':', e && e.message);
    });
  },

  // 兜底：枚举该 tab 下所有 frame，对 1688 frame 逐个注入
  // 适用于「webNavigation 事件没覆盖到」或「嵌套 1688 iframe」的情况
  async inject1688AllFrames(tabId) {
    if (tabId == null || !chrome.webNavigation) return;
    try {
      const frames = await chrome.webNavigation.getAllFrames({ tabId });
      if (!frames) return;
      const hits = frames.filter((f) => f.url && f.url.includes('1688.com'));
      Logger.info(`枚举 tab=${tabId} 共 ${frames.length} 个frame，其中1688 frame ${hits.length} 个`);
      for (const f of hits) {
        Logger.info('  -> 1688 frame:', f.url, 'frameId:', f.frameId);
        this.inject1688Hook(tabId, f.frameId);
      }
    } catch (e) {
      Logger.debug('枚举frame失败:', e && e.message);
    }
  },

  setup1688FrameInjection() {
    if (!chrome.webNavigation) {
      Logger.warn('webNavigation 不可用，无法主动注入1688拦截脚本');
      return;
    }

    const filter = { url: [{ hostSuffix: '1688.com' }] };

    const handler = (details) => {
      // 只处理子 frame（frameId > 0），插件 iframe 即在此
      if (!details || details.frameId === 0) return;
      Logger.info('🔎 检测到1688子frame导航:', details.url, 'frameId:', details.frameId);
      this.inject1688Hook(details.tabId, details.frameId);
      // 同时枚举整个 tab 兜底（覆盖嵌套 1688 iframe / 事件遗漏）
      this.inject1688AllFrames(details.tabId);
    };

    // onCommitted：尽早注入（页面脚本运行前）
    chrome.webNavigation.onCommitted.addListener(handler, filter);
    // onDOMContentLoaded：兜底重试，守卫保证不会重复 hook
    chrome.webNavigation.onDOMContentLoaded.addListener(handler, filter);

    Logger.info('1688子frame主动注入监听已启动');
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

  // 记录当前正在采集的商品上下文。
  // 关键：sync-inject(网页内容脚本)发出的 START_1688_COLLECTION 经 runtime.sendMessage
  // 只能到达后台，无法直达 1688 iframe 内的 collector，所以 collector 自身拿不到 productId。
  // 这里由后台统一持有上下文，入库时补全归属商品。
  handleUpdate1688SyncLimit(message, sendResponse) {
    const data = message.data || {};
    const syncLimit = data.syncLimit;
    if (syncLimit != null && syncLimit >= 1 && syncLimit <= 30) {
      // 更新当前上下文中的 syncLimit
      if (this.current1688Context) {
        this.current1688Context.syncLimit = syncLimit;
        StorageManager.set('gp_1688_context', this.current1688Context);
      } else {
        // 没有当前上下文时，只保存 syncLimit
        StorageManager.set('gp_1688_sync_limit', syncLimit);
      }
      Logger.info(`更新1688同步数量限制: syncLimit=${syncLimit}`);
    }
    sendResponse({ success: true });
  },

  handleStart1688Collection(message, sendResponse) {
    const data = message.data || {};
    // 保留已有的 syncLimit（如果消息中没有，则从当前上下文继承）
    const existingSyncLimit = this.current1688Context ? this.current1688Context.syncLimit : undefined;
    this.current1688Context = {
      tiktokProductId: data.tiktokProductId != null ? data.tiktokProductId : null,
      productId: data.productId != null ? data.productId : null,
      syncLimit: data.syncLimit != null ? data.syncLimit : existingSyncLimit,
      ts: Date.now(),
    };
    StorageManager.set('gp_1688_context', this.current1688Context);
    Logger.info(`记录1688采集上下文: TikTok商品ID=${this.current1688Context.tiktokProductId}, 商品表ID=${this.current1688Context.productId}, syncLimit=${this.current1688Context.syncLimit}`);
    sendResponse({ success: true });
  },

  async handleSave1688Data(message, sendResponse) {
    try {
      let { tiktokProductId, productId, products, syncLimit } = message.data;

      // collector 自身拿不到归属商品时，用后台记录的采集上下文补全
      if (productId == null || tiktokProductId == null || syncLimit == null) {
        const ctx = this.current1688Context || await StorageManager.get('gp_1688_context');
        if (ctx) {
          if (productId == null) productId = ctx.productId;
          if (tiktokProductId == null) tiktokProductId = ctx.tiktokProductId;
          if (syncLimit == null && ctx.syncLimit != null) syncLimit = ctx.syncLimit;
        }
      }

      // syncLimit 最终以 sync-inject 持续镜像的 gp_1688_sync_limit 为准（前端 localStorage 的最新值）
      const mirrored = await StorageManager.get('gp_1688_sync_limit');
      if (mirrored != null && mirrored >= 1 && mirrored <= 30) {
        syncLimit = mirrored;
      }

      Logger.info(`收到1688数据: TikTok商品ID=${tiktokProductId}, 商品表ID=${productId}, 商品数量=${products.length}, syncLimit=${syncLimit}`);

      if (productId == null) {
        Logger.warn('未知归属商品(productId 为空)，忽略本次1688数据');
        sendResponse({ success: false, error: { code: 'NO_PRODUCT_ID', message: '未确定归属商品，已忽略' } });
        return;
      }

      const token = await StorageManager.get(STORAGE_KEYS.TOKEN);
      if (!token) {
        sendResponse({ success: false, error: { code: 'AUTH_NOT_LOGGED_IN', message: '未登录' } });
        return;
      }

      // 入库前按当前登录来源刷新 API 地址，确保本地/生产不发错
      await this.refreshApiBase();
      const url = `${CONFIG.apiBaseUrl}/1688/products/batch`;
      Logger.info(`1688入库目标: ${url}`);
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
          sync_limit: syncLimit != null ? syncLimit : 5,
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

    // 先更新采集上下文，确保入库时使用正确的商品ID
    this.current1688Context = {
      tiktokProductId: tiktokProductId != null ? tiktokProductId : null,
      productId: productId != null ? productId : null,
      ts: Date.now(),
    };
    StorageManager.set('gp_1688_context', this.current1688Context);
    Logger.info(`更新1688采集上下文: TikTok商品ID=${this.current1688Context.tiktokProductId}, 商品表ID=${this.current1688Context.productId}`);

    chrome.tabs.create({ url, active: true }, (tab) => {
      Logger.info('打开1688标签页:', tab.id, 'TikTok商品ID:', tiktokProductId, '商品表ID:', productId);

      // 等待页面加载后，查找1688 iframe并发送采集指令
      const sendStartCommand = (retryCount) => {
        chrome.webNavigation.getAllFrames({ tabId: tab.id }, (frames) => {
          if (!frames || frames.length === 0) {
            if (retryCount < 10) {
              setTimeout(() => sendStartCommand(retryCount + 1), 500);
            } else {
              Logger.error('未找到1688 iframe，放弃发送采集指令');
            }
            return;
          }

          const frame1688 = frames.find(f => f.url && f.url.includes('1688.com'));
          if (frame1688) {
            Logger.info('找到1688 iframe, frameId:', frame1688.frameId);
            chrome.tabs.sendMessage(tab.id, {
              type: 'START_1688_COLLECTION',
              data: { 
                tiktokProductId: tiktokProductId,
                productId: productId,
              },
            }, { frameId: frame1688.frameId }, (response) => {
              if (chrome.runtime.lastError) {
                Logger.error('发送采集指令失败:', chrome.runtime.lastError);
                if (retryCount < 10) {
                  setTimeout(() => sendStartCommand(retryCount + 1), 500);
                }
              } else {
                Logger.info('采集指令发送成功');
              }
            });
          } else {
            if (retryCount < 10) {
              setTimeout(() => sendStartCommand(retryCount + 1), 500);
            } else {
              Logger.error('未找到1688 iframe，放弃发送采集指令');
            }
          }
        });
      };

      setTimeout(() => sendStartCommand(0), 1000);
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
