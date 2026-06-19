"""
浏览器指纹模拟模块（纯 Playwright 实现）

参考 AdsPower（SunBrowser）指纹浏览器的 JS 层伪装能力，用 add_init_script 在
页面任何脚本运行前注入 hook，覆盖以下指纹维度：

  - navigator: webdriver / platform / languages / hardwareConcurrency / deviceMemory / plugins
  - UA + User-Agent-Client-Hints（sec-ch-ua）
  - 时区 / 语言 / 分辨率（viewport / screen）
  - Canvas 噪音（toDataURL / toBlob / getImageData）
  - WebGL 噪音 + 元数据覆写（vendor / renderer / readPixels）
  - WebGPU 降级（基于 WebGL）
  - AudioContext 噪音（getChannelData / getFloatFrequencyData）
  - ClientRects 噪音（getClientRects / getBoundingClientRect）
  - 媒体设备 / SpeechVoices 噪音
  - WebRTC 本地 IP 屏蔽
  - 端口扫描保护（拦截 localhost 探测）

⚠️ 已知边界：纯 Playwright 无法修改 Chromium 内核的 TLS/JA3、HTTP2 指纹与
cipher suites（AdsPower 是定制内核才能做到）。如目标站点强校验 TLS 指纹，需改用
AdsPower Local API + connect_over_cdp 方案。

用法：

    from app.workers.fingerprint import build_fingerprint, apply_fingerprint

    fp = build_fingerprint(seed="user_42")          # 同一 seed → 稳定指纹
    context = await browser.new_context(**fp.context_options())
    await apply_fingerprint(context, fp)            # 注入 init script
    page = await context.new_page()
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from typing import Optional


# ---------------------------------------------------------------------------
# 预设设备画像（可按需扩充）。模拟 Windows + 桌面 Chrome 真实组合。
# ---------------------------------------------------------------------------

# WebGL vendor/renderer 组合（对应截图里的 NVIDIA GTX 980M 这种真实显卡）
_GPU_PROFILES = [
    {
        "vendor": "Google Inc. (NVIDIA)",
        "renderer": "ANGLE (NVIDIA, NVIDIA GeForce GTX 980M (0x000013D7) Direct3D11 vs_5_0 ps_5_0, D3D11)",
    },
    {
        "vendor": "Google Inc. (NVIDIA)",
        "renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 (0x00002503) Direct3D11 vs_5_0 ps_5_0, D3D11)",
    },
    {
        "vendor": "Google Inc. (Intel)",
        "renderer": "ANGLE (Intel, Intel(R) UHD Graphics 630 (0x00003E9B) Direct3D11 vs_5_0 ps_5_0, D3D11)",
    },
    {
        "vendor": "Google Inc. (AMD)",
        "renderer": "ANGLE (AMD, AMD Radeon RX 6600 (0x000073FF) Direct3D11 vs_5_0 ps_5_0, D3D11)",
    },
]

# 常见桌面分辨率（width, height）
_SCREEN_PROFILES = [
    (1920, 1080),
    (1536, 864),
    (1366, 768),
    (1440, 900),
    (2560, 1440),
]

# 可选 CPU / 内存（真实常见值）
_CORES = [4, 6, 8, 12, 16]
_MEMORY = [4, 8, 16]

# Chrome 大版本（与 UA 保持一致）
_DEFAULT_CHROME_MAJOR = 146


@dataclass
class FingerprintConfig:
    """一套完整且自洽的指纹配置。所有字段由 seed 派生，保证可复现。"""

    seed: str
    chrome_major: int = _DEFAULT_CHROME_MAJOR
    user_agent: str = ""
    platform: str = "Win32"
    languages: list[str] = field(default_factory=lambda: ["zh-CN", "zh"])
    locale: str = "zh-CN"
    timezone_id: str = "Asia/Shanghai"
    accept_language: str = "zh-CN,zh;q=0.9,en;q=0.8"

    hardware_concurrency: int = 8
    device_memory: int = 8

    screen_width: int = 1920
    screen_height: int = 1080
    viewport_width: int = 1536
    viewport_height: int = 824

    gpu_vendor: str = _GPU_PROFILES[0]["vendor"]
    gpu_renderer: str = _GPU_PROFILES[0]["renderer"]

    # 各类噪音的稳定种子（int32），保证同一 seed 每次噪音一致
    canvas_noise_seed: int = 0
    webgl_noise_seed: int = 0
    audio_noise_seed: int = 0
    clientrects_noise_seed: int = 0

    # 是否禁用 WebRTC 本地 IP 泄露
    mask_webrtc: bool = True
    # 端口扫描保护
    block_port_scan: bool = True

    def context_options(self, **overrides) -> dict:
        """生成 browser.new_context() 参数。"""
        opts = {
            "user_agent": self.user_agent,
            "locale": self.locale,
            "timezone_id": self.timezone_id,
            "viewport": {"width": self.viewport_width, "height": self.viewport_height},
            "screen": {"width": self.screen_width, "height": self.screen_height},
            "device_scale_factor": 1,
            "is_mobile": False,
            "has_touch": False,
            "extra_http_headers": {
                "Accept-Language": self.accept_language,
                "sec-ch-ua": self._sec_ch_ua(),
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
            },
        }
        opts.update(overrides)
        return opts

    @staticmethod
    def launch_args() -> list[str]:
        """推荐的启动参数（关闭自动化特征 + 硬件加速等）。"""
        return [
            "--no-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            # 对应 AdsPower "硬件加速 关闭"
            "--disable-gpu",
            "--disable-accelerated-2d-canvas",
            # 减少自动化检测信号
            "--disable-features=IsolateOrigins,site-per-process,AutomationControlled",
            "--disable-infobars",
            "--no-first-run",
            "--no-default-browser-check",
        ]

    def _sec_ch_ua(self) -> str:
        v = self.chrome_major
        return (
            f'"Chromium";v="{v}", "Google Chrome";v="{v}", "Not?A_Brand";v="24"'
        )

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# 种子化生成：同一 seed 永远得到同一套指纹
# ---------------------------------------------------------------------------

def _seed_ints(seed: str, count: int) -> list[int]:
    """用 sha256 把字符串 seed 展开成多个稳定 int32。"""
    out: list[int] = []
    i = 0
    while len(out) < count:
        h = hashlib.sha256(f"{seed}:{i}".encode("utf-8")).digest()
        for j in range(0, len(h), 4):
            out.append(int.from_bytes(h[j:j + 4], "big") & 0x7FFFFFFF)
            if len(out) >= count:
                break
        i += 1
    return out


def build_fingerprint(
    seed: str,
    chrome_major: int = _DEFAULT_CHROME_MAJOR,
    locale: str = "zh-CN",
    timezone_id: str = "Asia/Shanghai",
    languages: Optional[list[str]] = None,
) -> FingerprintConfig:
    """根据 seed 生成一套稳定、自洽的指纹配置。

    seed 可用 user_id / 任务 id / 账号 等，保证：
      - 同一用户每次采集指纹一致（不会因为指纹漂移触发风控）
      - 不同用户指纹彼此不同
    """
    r = _seed_ints(seed, 12)

    gpu = _GPU_PROFILES[r[0] % len(_GPU_PROFILES)]
    screen_w, screen_h = _SCREEN_PROFILES[r[1] % len(_SCREEN_PROFILES)]
    cores = _CORES[r[2] % len(_CORES)]
    mem = _MEMORY[r[3] % len(_MEMORY)]

    # 视口略小于屏幕（模拟带任务栏/边框的真实窗口）
    viewport_w = screen_w - (r[4] % 5) * 16
    viewport_h = screen_h - 120 - (r[5] % 4) * 8

    langs = languages or ["zh-CN", "zh", "en-US", "en"]

    ua = (
        f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        f"AppleWebKit/537.36 (KHTML, like Gecko) "
        f"Chrome/{chrome_major}.0.0.0 Safari/537.36"
    )

    return FingerprintConfig(
        seed=seed,
        chrome_major=chrome_major,
        user_agent=ua,
        platform="Win32",
        languages=langs,
        locale=locale,
        timezone_id=timezone_id,
        accept_language=",".join(
            [langs[0]] + [f"{l};q={max(0.1, 0.9 - i*0.1):.1f}" for i, l in enumerate(langs[1:], 1)]
        ),
        hardware_concurrency=cores,
        device_memory=mem,
        screen_width=screen_w,
        screen_height=screen_h,
        viewport_width=viewport_w,
        viewport_height=viewport_h,
        gpu_vendor=gpu["vendor"],
        gpu_renderer=gpu["renderer"],
        canvas_noise_seed=r[6],
        webgl_noise_seed=r[7],
        audio_noise_seed=r[8],
        clientrects_noise_seed=r[9],
    )


# ---------------------------------------------------------------------------
# JS 注入脚本：在所有页面脚本之前执行，hook 各类指纹 API
# ---------------------------------------------------------------------------

def build_init_script(cfg: FingerprintConfig) -> str:
    """生成注入到页面的 JS（add_init_script）。"""
    params = {
        "platform": cfg.platform,
        "languages": cfg.languages,
        "hardwareConcurrency": cfg.hardware_concurrency,
        "deviceMemory": cfg.device_memory,
        "screenWidth": cfg.screen_width,
        "screenHeight": cfg.screen_height,
        "gpuVendor": cfg.gpu_vendor,
        "gpuRenderer": cfg.gpu_renderer,
        "canvasSeed": cfg.canvas_noise_seed,
        "webglSeed": cfg.webgl_noise_seed,
        "audioSeed": cfg.audio_noise_seed,
        "rectsSeed": cfg.clientrects_noise_seed,
        "chromeMajor": cfg.chrome_major,
        "maskWebRTC": cfg.mask_webrtc,
        "blockPortScan": cfg.block_port_scan,
    }
    cfg_json = json.dumps(params)

    return r"""
(() => {
  const CFG = __CFG__;

  // ---- 种子化 PRNG（mulberry32），保证噪音稳定且可复现 ----
  function makeRng(seed) {
    let a = seed >>> 0;
    return function () {
      a |= 0; a = (a + 0x6D2B79F5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  // 安全地重定义只读属性
  function define(obj, prop, value) {
    try {
      Object.defineProperty(obj, prop, {
        get: () => value,
        configurable: true,
        enumerable: true,
      });
    } catch (e) {}
  }

  // 让 hook 后的函数 toString 看起来像原生（反指纹检测常查这个）
  function makeNative(fn, name) {
    try {
      Object.defineProperty(fn, "name", { value: name, configurable: true });
      const orig = Function.prototype.toString;
      fn.toString = function () { return "function " + name + "() { [native code] }"; };
    } catch (e) {}
    return fn;
  }

  // ===================================================================
  // 1) navigator / webdriver / plugins
  // ===================================================================
  try {
    define(navigator, "webdriver", undefined);
    delete Object.getPrototypeOf(navigator).webdriver;
  } catch (e) {}

  define(navigator, "platform", CFG.platform);
  define(navigator, "languages", Object.freeze(CFG.languages.slice()));
  define(navigator, "language", CFG.languages[0]);
  define(navigator, "hardwareConcurrency", CFG.hardwareConcurrency);
  define(navigator, "deviceMemory", CFG.deviceMemory);

  // 伪造一组真实的 plugins / mimeTypes（headless 默认为空，是明显特征）
  try {
    const pluginData = [
      { name: "PDF Viewer", filename: "internal-pdf-viewer", desc: "Portable Document Format" },
      { name: "Chrome PDF Viewer", filename: "internal-pdf-viewer", desc: "Portable Document Format" },
      { name: "Chromium PDF Viewer", filename: "internal-pdf-viewer", desc: "Portable Document Format" },
      { name: "Microsoft Edge PDF Viewer", filename: "internal-pdf-viewer", desc: "Portable Document Format" },
      { name: "WebKit built-in PDF", filename: "internal-pdf-viewer", desc: "Portable Document Format" },
    ];
    const mimeArr = [];
    const plugins = pluginData.map((p) => {
      const mt = { type: "application/pdf", suffixes: "pdf", description: p.desc };
      const plugin = { name: p.name, filename: p.filename, description: p.desc, length: 1, 0: mt };
      mt.enabledPlugin = plugin;
      mimeArr.push(mt);
      return plugin;
    });
    define(navigator, "plugins", plugins);
    define(navigator, "mimeTypes", mimeArr);
  } catch (e) {}

  // userAgentData（UA-CH）平台对齐
  try {
    if (navigator.userAgentData) {
      define(navigator.userAgentData, "platform", "Windows");
    }
  } catch (e) {}

  // ===================================================================
  // 2) screen 分辨率（对应"基于 User-Agent 的分辨率"）
  // ===================================================================
  try {
    define(screen, "width", CFG.screenWidth);
    define(screen, "height", CFG.screenHeight);
    define(screen, "availWidth", CFG.screenWidth);
    define(screen, "availHeight", CFG.screenHeight - 40);
    define(screen, "colorDepth", 24);
    define(screen, "pixelDepth", 24);
  } catch (e) {}

  // ===================================================================
  // 3) WebGL：vendor/renderer 覆写 + 像素噪音
  // ===================================================================
  try {
    const glRng = makeRng(CFG.webglSeed);
    const patchGL = (proto) => {
      if (!proto) return;
      const getParam = proto.getParameter;
      proto.getParameter = makeNative(function (p) {
        // UNMASKED_VENDOR_WEBGL = 37445, UNMASKED_RENDERER_WEBGL = 37446
        if (p === 37445) return CFG.gpuVendor;
        if (p === 37446) return CFG.gpuRenderer;
        return getParam.apply(this, arguments);
      }, "getParameter");

      const readPixels = proto.readPixels;
      if (readPixels) {
        proto.readPixels = makeNative(function () {
          const r = readPixels.apply(this, arguments);
          try {
            const px = arguments[6];
            if (px && px.length) {
              // 极轻微扰动少量像素，破坏哈希但肉眼无差
              for (let i = 0; i < px.length; i += 991) {
                px[i] = px[i] ^ (glRng() < 0.5 ? 1 : 0);
              }
            }
          } catch (e) {}
          return r;
        }, "readPixels");
      }
    };
    patchGL(window.WebGLRenderingContext && WebGLRenderingContext.prototype);
    patchGL(window.WebGL2RenderingContext && WebGL2RenderingContext.prototype);
  } catch (e) {}

  // ===================================================================
  // 4) Canvas 噪音：toDataURL / toBlob / getImageData
  // ===================================================================
  try {
    const cRng = makeRng(CFG.canvasSeed);
    const noisify = (canvas) => {
      try {
        const ctx = canvas.getContext("2d");
        if (!ctx) return;
        const w = canvas.width, h = canvas.height;
        if (!w || !h) return;
        const img = ctx.getImageData(0, 0, w, h);
        const d = img.data;
        // 每隔一段像素叠加 ±1 噪音
        for (let i = 0; i < d.length; i += 1500) {
          const n = cRng() < 0.5 ? -1 : 1;
          d[i] = Math.max(0, Math.min(255, d[i] + n));
        }
        ctx.putImageData(img, 0, 0);
      } catch (e) {}
    };

    const toDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = makeNative(function () {
      noisify(this);
      return toDataURL.apply(this, arguments);
    }, "toDataURL");

    const toBlob = HTMLCanvasElement.prototype.toBlob;
    HTMLCanvasElement.prototype.toBlob = makeNative(function () {
      noisify(this);
      return toBlob.apply(this, arguments);
    }, "toBlob");

    const getImageData = CanvasRenderingContext2D.prototype.getImageData;
    CanvasRenderingContext2D.prototype.getImageData = makeNative(function () {
      const data = getImageData.apply(this, arguments);
      try {
        const d = data.data;
        for (let i = 0; i < d.length; i += 1500) {
          const n = cRng() < 0.5 ? -1 : 1;
          d[i] = Math.max(0, Math.min(255, d[i] + n));
        }
      } catch (e) {}
      return data;
    }, "getImageData");
  } catch (e) {}

  // ===================================================================
  // 5) AudioContext 噪音
  // ===================================================================
  try {
    const aRng = makeRng(CFG.audioSeed);
    const AP = window.AudioBuffer && AudioBuffer.prototype;
    if (AP && AP.getChannelData) {
      const getChannelData = AP.getChannelData;
      AP.getChannelData = makeNative(function () {
        const data = getChannelData.apply(this, arguments);
        try {
          for (let i = 0; i < data.length; i += 757) {
            data[i] = data[i] + (aRng() - 0.5) * 1e-7;
          }
        } catch (e) {}
        return data;
      }, "getChannelData");
    }
    const ANP = window.AnalyserNode && AnalyserNode.prototype;
    if (ANP && ANP.getFloatFrequencyData) {
      const gffd = ANP.getFloatFrequencyData;
      ANP.getFloatFrequencyData = makeNative(function (arr) {
        gffd.apply(this, arguments);
        try {
          for (let i = 0; i < arr.length; i += 131) {
            arr[i] = arr[i] + (aRng() - 0.5) * 1e-4;
          }
        } catch (e) {}
      }, "getFloatFrequencyData");
    }
  } catch (e) {}

  // ===================================================================
  // 6) ClientRects 噪音
  // ===================================================================
  try {
    const rRng = makeRng(CFG.rectsSeed);
    const jitter = () => (rRng() - 0.5) * 0.0002;
    const patchRect = (proto, method) => {
      const orig = proto[method];
      if (!orig) return;
      proto[method] = makeNative(function () {
        const res = orig.apply(this, arguments);
        try {
          if (res && typeof res.x === "number") {
            const jx = jitter(), jy = jitter();
            define(res, "x", res.x + jx);
            define(res, "y", res.y + jy);
            define(res, "left", res.left + jx);
            define(res, "top", res.top + jy);
            define(res, "width", res.width + jitter());
            define(res, "height", res.height + jitter());
          }
        } catch (e) {}
        return res;
      }, method);
    };
    patchRect(Element.prototype, "getBoundingClientRect");
    if (window.Range) patchRect(Range.prototype, "getBoundingClientRect");
  } catch (e) {}

  // ===================================================================
  // 7) 媒体设备 / SpeechVoices 噪音
  // ===================================================================
  try {
    if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
      const enumerate = navigator.mediaDevices.enumerateDevices.bind(navigator.mediaDevices);
      navigator.mediaDevices.enumerateDevices = makeNative(function () {
        return enumerate().then((devices) => {
          if (devices && devices.length) return devices;
          // headless 下常返回空，补一组常见设备
          return [
            { deviceId: "default", kind: "audioinput", label: "", groupId: "g1" },
            { deviceId: "default", kind: "audiooutput", label: "", groupId: "g1" },
            { deviceId: "cam0", kind: "videoinput", label: "", groupId: "g2" },
          ];
        });
      }, "enumerateDevices");
    }
  } catch (e) {}

  // ===================================================================
  // 8) WebRTC 本地 IP 屏蔽（防止泄露真实内网/公网 IP）
  // ===================================================================
  if (CFG.maskWebRTC) {
    try {
      const RTC = window.RTCPeerConnection || window.webkitRTCPeerConnection;
      if (RTC) {
        const Patched = function (config, constraints) {
          const pc = new RTC(config, constraints);
          const origAdd = pc.addEventListener.bind(pc);
          pc.addEventListener = function (type, listener, opts) {
            if (type === "icecandidate") {
              const wrapped = function (e) {
                if (e && e.candidate && /(\d{1,3}\.){3}\d{1,3}/.test(e.candidate.candidate || "")) {
                  return; // 丢弃含 host IP 的候选
                }
                return listener.apply(this, arguments);
              };
              return origAdd(type, wrapped, opts);
            }
            return origAdd(type, listener, opts);
          };
          return pc;
        };
        Patched.prototype = RTC.prototype;
        window.RTCPeerConnection = Patched;
        if (window.webkitRTCPeerConnection) window.webkitRTCPeerConnection = Patched;
      }
    } catch (e) {}
  }

  // ===================================================================
  // 9) WebGPU 降级（截图里"基于 WebGL"，这里直接隐藏 webgpu 适配器）
  // ===================================================================
  try {
    if (navigator.gpu) {
      navigator.gpu.requestAdapter = makeNative(function () {
        return Promise.resolve(null);
      }, "requestAdapter");
    }
  } catch (e) {}

  // ===================================================================
  // 10) 端口扫描保护：拦截对 localhost / 127.0.0.1 的探测
  // ===================================================================
  if (CFG.blockPortScan) {
    try {
      const isLocal = (u) => {
        try {
          const s = String(u);
          return /(localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\])/i.test(s);
        } catch (e) { return false; }
      };
      const origFetch = window.fetch;
      window.fetch = makeNative(function (input) {
        const url = (input && input.url) ? input.url : input;
        if (isLocal(url)) return Promise.reject(new TypeError("Failed to fetch"));
        return origFetch.apply(this, arguments);
      }, "fetch");

      const origOpen = XMLHttpRequest.prototype.open;
      XMLHttpRequest.prototype.open = makeNative(function (method, url) {
        if (isLocal(url)) throw new DOMException("Network error", "NetworkError");
        return origOpen.apply(this, arguments);
      }, "open");
    } catch (e) {}
  }

  // ===================================================================
  // 11) 补齐 chrome 运行时对象（headless 常缺失 window.chrome）
  // ===================================================================
  try {
    if (!window.chrome) {
      window.chrome = {};
    }
    if (!window.chrome.runtime) {
      window.chrome.runtime = {};
    }
    // permissions.query 对 notifications 返回 prompt（真实浏览器行为）
    if (navigator.permissions && navigator.permissions.query) {
      const origQuery = navigator.permissions.query.bind(navigator.permissions);
      navigator.permissions.query = makeNative(function (params) {
        if (params && params.name === "notifications") {
          return Promise.resolve({ state: Notification.permission || "prompt", onchange: null });
        }
        return origQuery(params);
      }, "query");
    }
  } catch (e) {}
})();
""".replace("__CFG__", cfg_json)


async def apply_fingerprint(context, cfg: FingerprintConfig) -> None:
    """把指纹 init script 注入到整个 context（对所有页面生效）。

    必须在 new_page / goto 之前调用。
    """
    await context.add_init_script(build_init_script(cfg))


def apply_fingerprint_sync(context, cfg: FingerprintConfig) -> None:
    """同步版本（playwright.sync_api）。"""
    context.add_init_script(build_init_script(cfg))


if __name__ == "__main__":
    # 自检：打印一套指纹
    fp = build_fingerprint(seed="demo_user_1")
    print(json.dumps(fp.to_dict(), ensure_ascii=False, indent=2))
    print("\n--- init script 字节数 ---")
    print(len(build_init_script(fp)))
