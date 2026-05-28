#!/usr/bin/env python3
"""
TikTok验证码fp替换脚本
在过验证码时拦截并替换/captcha/get和/captcha/verify接口的fp参数
不修改原有tiktok_captcha_solver.py代码
"""

import asyncio
import json
import sys
import os

from playwright.async_api import async_playwright

# 导入原有的验证码解决器
sys.path.append(os.path.dirname(__file__))
from tiktok_captcha_solver import TikTokCaptchaSolver


class FpReplacerCaptchaSolver(TikTokCaptchaSolver):
    """
    继承原有的TikTokCaptchaSolver，添加fp替换功能
    """
    
    def __init__(self, target_fp: str, **kwargs):
        """
        初始化
        :param target_fp: 要替换的目标fp值
        :param kwargs: 传递给父类的其他参数
        """
        super().__init__(**kwargs)
        self.target_fp = target_fp
        self.intercepted_requests = []
    
    async def init_browser(self):
        """重写浏览器初始化，添加请求拦截"""
        self.playwright = await async_playwright().start()
        
        if self.browser_type == "firefox":
            self.browser = await self.playwright.firefox.launch(
                headless=False,
                args=['--disable-blink-features=AutomationControlled']
            )
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0'
            )
        else:
            self.browser = await self.playwright.chromium.launch(
                headless=False,
                args=['--disable-blink-features=AutomationControlled', '--disable-setuid-sandbox', '--no-sandbox']
            )
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
        
        self.page = await self.context.new_page()
        
        # 添加反检测脚本
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        # 设置请求拦截
        await self.setup_request_interception()
        
        print(f"浏览器初始化完成: {self.browser_type}")
        print(f"目标fp: {self.target_fp}")
    
    async def setup_request_interception(self):
        """设置请求拦截，替换fp参数"""
        
        async def handle_request(route, request):
            url = request.url
            
            # 检查是否是/captcha/get或/captcha/verify接口
            if '/captcha/get' in url or '/captcha/verify' in url:
                print(f"\n[拦截请求] {url}")
                
                # 替换fp参数
                modified_url = self.replace_fp_in_url(url, self.target_fp)
                
                if modified_url != url:
                    print(f"[替换fp] 原fp -> 新fp: {self.target_fp}")
                    print(f"[修改URL] {modified_url}")
                    self.intercepted_requests.append({
                        'original': url,
                        'modified': modified_url,
                        'type': 'captcha_get' if '/captcha/get' in url else 'captcha_verify'
                    })
                
                # 继续请求（使用修改后的URL）
                await route.continue_(url=modified_url)
            else:
                # 其他请求正常放行
                await route.continue_()
        
        # 启用请求拦截
        await self.page.route("**/*", handle_request)
    
    def replace_fp_in_url(self, url: str, new_fp: str) -> str:
        """
        替换URL中的fp参数
        :param url: 原始URL
        :param new_fp: 新的fp值
        :return: 替换后的URL
        """
        if 'fp=' not in url:
            return url
        
        # 分割URL和查询参数
        if '?' in url:
            base_url, query_string = url.split('?', 1)
        else:
            return url
        
        # 解析查询参数
        params = query_string.split('&')
        new_params = []
        
        for param in params:
            if param.startswith('fp='):
                # 替换fp参数
                new_params.append(f'fp={new_fp}')
                print(f"  找到fp参数，已替换")
            else:
                new_params.append(param)
        
        # 重新组装URL
        return f"{base_url}?{'&'.join(new_params)}"
    
    async def open_captcha_page(self, url: str):
        """打开验证码页面（带fp替换）"""
        print(f"\n=== 开始处理验证码 ===")
        print(f"目标URL: {url}")
        print(f"将替换fp为: {self.target_fp}")
        
        # 先替换URL中的fp
        modified_url = self.replace_fp_in_url(url, self.target_fp)
        
        print(f"正在打开页面: {modified_url}")
        await self.page.goto(modified_url, wait_until="domcontentloaded", timeout=60000)
        print("等待页面加载...")
        await asyncio.sleep(5)
        await self.page.wait_for_load_state("networkidle", timeout=60000)
        await asyncio.sleep(5)
        print("页面加载完成")
    
    def print_intercept_summary(self):
        """打印拦截统计"""
        print(f"\n=== fp替换统计 ===")
        print(f"共拦截 {len(self.intercepted_requests)} 个请求")
        
        captcha_get_count = sum(1 for r in self.intercepted_requests if r['type'] == 'captcha_get')
        captcha_verify_count = sum(1 for r in self.intercepted_requests if r['type'] == 'captcha_verify')
        
        print(f"/captcha/get 接口: {captcha_get_count} 次")
        print(f"/captcha/verify 接口: {captcha_verify_count} 次")
        print(f"使用的fp: {self.target_fp}")


async def main(target_url: str, target_fp: str, browser_type: str = "chromium"):
    """
    主函数
    :param target_url: 目标URL
    :param target_fp: 要替换的fp值
    :param browser_type: 浏览器类型
    """
    solver = FpReplacerCaptchaSolver(
        target_fp=target_fp,
        browser_type=browser_type
    )
    
    try:
        await solver.init_browser()
        await solver.open_captcha_page(target_url)
        
        captcha_found = await solver.check_captcha_exists()
        
        if not captcha_found:
            print("未检测到验证码，验证码可能已经通过")
            await solver.save_cookies()
            solver.print_intercept_summary()
            print("\n=== 验证码已通过 ===")
            print(f"Cookies已保存到: {solver.cookies_file}")
            return
        
        await solver.get_captcha_images()
        
        distance = solver.calculate_slide_distance()
        
        await solver.drag_slider(distance)
        
        await asyncio.sleep(5)
        
        await solver.save_cookies()
        
        solver.print_intercept_summary()
        
        print("\n=== 验证码处理完成 ===")
        print(f"滑动距离: {distance}px")
        print(f"Cookies已保存到: {solver.cookies_file}")
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n请查看浏览器中的验证码图片...")
        await asyncio.sleep(30)
        await solver.close()


if __name__ == "__main__":
    """
    tiktok PC 风控:
        如果复制FP取playwright过会触发风控 IP访问商品跳登录,之前浏览器返回json当前地区无此商品的信息
        过一段时间会解
    """
    # 使用示例
    browser_type = 'chromium'
    
    # 目标URL（包含原始fp）
    target_url = "https://shop.tiktok.com/view/product/1734463142591760128?region=TH&locale=zh-CN"
    #             https://shop.tiktok.com/view/product/1729493772107089424?region=SG&locale=en-US
    
    # 要替换的目标fp（从你的服务器获取的已通过验证的fp）
    target_fp = "verify_mokdzxjz_21pa9vsT_WMB1_46lq_BuIZ_7GSTtH16jDQo"
    
    print("=" * 60)
    print("TikTok验证码fp替换脚本")
    print("=" * 60)
    print(f"原始URL: {target_url}")
    print(f"目标fp: {target_fp}")
    print("=" * 60)
    
    asyncio.run(main(target_url, target_fp, browser_type))
