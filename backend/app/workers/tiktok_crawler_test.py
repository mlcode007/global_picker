import asyncio
import time

from playwright.async_api import async_playwright

from app.workers.fingerprint import build_fingerprint, apply_fingerprint


async def main():
    # 用 seed 生成一套稳定指纹（同一 seed 每次结果一致；换 seed 得到不同指纹）
    fp = build_fingerprint(seed="tiktok_test_user")
    print("本次指纹:")
    print(f"  UA       : {fp.user_agent}")
    print(f"  GPU      : {fp.gpu_renderer}")
    print(f"  分辨率   : {fp.screen_width}x{fp.screen_height} (viewport {fp.viewport_width}x{fp.viewport_height})")
    print(f"  CPU/RAM  : {fp.hardware_concurrency} 核 / {fp.device_memory} GB")
    print(f"  时区/语言: {fp.timezone_id} / {fp.locale}")

    async with async_playwright() as p:
        # 启动浏览器（headless=False 可以看到窗口，True 则无头）
        browser = await p.chromium.launch(
            headless=False,
            slow_mo=200,
            args=fp.launch_args(),
        )

        # 通过 context 统一伪装 UA / 语言 / 时区 / 视口 / UA-CH 等
        context = await browser.new_context(**fp.context_options())

        # 注入指纹 hook（Canvas/WebGL/Audio/ClientRects/WebRTC/...），必须在 new_page 之前
        # await apply_fingerprint(context, fp)

        page = await context.new_page()

        # 1. 先用指纹检测站点验证伪装效果（可选）
        # await page.goto("https://abrahamjuliot.github.io/creepjs/", timeout=120000)
        # await page.wait_for_timeout(8000)
        # await page.screenshot(path="fingerprint_check.png", full_page=True)
        # print("已保存指纹检测截图: fingerprint_check.png")

        # 2. 打开目标商品页面
        await page.goto(
            "https://shop.tiktok.com/view/product/1731103839855020720?region=PH&locale=zh-CN&source=agency"
        )

        # 3. 截图保存
        # await page.screenshot(path="baidu_home.png")

        # 4. 等待页面加载
        try:
            await page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:
            pass

        time.sleep(60 * 5)
        # 关闭浏览器
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
