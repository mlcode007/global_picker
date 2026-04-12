/**
 * 云手机 Web SDK（星界）
 * 脚本: https://console.chinac.com/front/JsSdk/JsSdk-1.0.js
 *
 * 注意：window.XingJieSdk 为单例，多次 init 只会保留最后一个容器内的画面。
 * 多路预览需使用 window.XingJieSdkObj 构造独立实例（每实例一个 iframe）。
 */

const SDK_SRC = 'https://console.chinac.com/front/JsSdk/JsSdk-1.0.js'

let loadPromise = null

export function loadChinacJsSdk() {
  if (typeof window !== 'undefined' && window.XingJieSdkObj) {
    return Promise.resolve(window.XingJieSdk)
  }
  if (loadPromise) return loadPromise

  loadPromise = new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[src="${SDK_SRC}"]`)
    if (existing) {
      const done = () => {
        if (window.XingJieSdkObj) resolve(window.XingJieSdk)
        else reject(new Error('JsSdk 已加载但未暴露 XingJieSdkObj'))
      }
      if (window.XingJieSdkObj) {
        done()
        return
      }
      existing.addEventListener('load', done)
      existing.addEventListener('error', () => reject(new Error('加载云手机 JsSDK 失败')))
      return
    }
    const s = document.createElement('script')
    s.src = SDK_SRC
    s.async = true
    s.onload = () => {
      if (window.XingJieSdkObj) resolve(window.XingJieSdk)
      else reject(new Error('JsSdk 加载后未暴露 XingJieSdkObj'))
    }
    s.onerror = () => reject(new Error('加载云手机 JsSDK 失败'))
    document.head.appendChild(s)
  })
  return loadPromise
}

/** 创建独立 SDK 实例（多设备预览时每个容器一个实例） */
export function createSdkInstance() {
  const Ctor = typeof window !== 'undefined' ? window.XingJieSdkObj : null
  if (!Ctor || typeof Ctor !== 'function') {
    throw new Error('XingJieSdkObj 未就绪')
  }
  return new Ctor()
}

export function destroySdkInstance(sdk) {
  if (sdk && typeof sdk.destroy === 'function') {
    try {
      sdk.destroy()
    } catch {
      /* ignore */
    }
  }
}

/** 兼容旧代码：销毁全局单例（仅用于无需多实例时） */
export function destroyChinacSdk() {
  destroySdkInstance(typeof window !== 'undefined' ? window.XingJieSdk : null)
}

/** 同设备两次 init 最小间隔（与上次 init 时刻对齐） */
const INIT_MIN_GAP_MS = 6000

const lastInitAtByDevice = new Map()

/**
 * @param {object} sdk - createSdkInstance() 的返回值，勿用全局 XingJieSdk 做多路
 * @param {string} playDivId
 * @param {string} url
 * @param {object} [extra] 可传 deviceId（云手机 ID），用于跨列表/弹窗节流同一设备的 init
 */
export async function initChinacPlayer(sdk, playDivId, url, extra = {}) {
  if (!sdk || typeof sdk.init !== 'function') {
    throw new Error('XingJieSdk 未就绪')
  }

  const { deviceId, ...restExtra } = extra

  if (deviceId != null && deviceId !== '') {
    const last = lastInitAtByDevice.get(deviceId)
    const now = Date.now()
    if (last != null) {
      const elapsed = now - last
      if (elapsed < INIT_MIN_GAP_MS) {
        await new Promise((r) => setTimeout(r, INIT_MIN_GAP_MS - elapsed))
      }
    }
    lastInitAtByDevice.set(deviceId, Date.now())
  }

  sdk.onInitSuccess = () => {
    console.log('[XingJieSdk] onInitSuccess')
  }
  sdk.onVideoConnChange = (status, code) => {
    console.log('[XingJieSdk] onVideoConnChange', status, code)
  }
  sdk.onOrientationChange = (orientation, w, h) => {
    console.log('[XingJieSdk] onOrientationChange', orientation, w, h)
  }

  const config = {
    playDivId,
    url,
    autoConnect: true,
    mute: true,
    cameraMic: false,
    showBottomBar: true,
    autoRotate: false,
    resolution: '720P',
    displayWidth: 0,
    showScreenShotBtn: true,
    showCameraBtn: true,
    showCleanAppBtn: true,
    showShakeBtn: true,
    showClipboardBtn: true,
    lang: 'zh_CN',
    ...restExtra,
  }
  sdk.init(config)
}

export function playContainerId(phoneId) {
  return `xingjie-cp-${String(phoneId).replace(/[^a-zA-Z0-9_-]/g, '_')}`
}
