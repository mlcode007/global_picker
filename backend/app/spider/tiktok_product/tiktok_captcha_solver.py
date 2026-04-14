#!/usr/bin/env python3
"""
TikTok滑块验证码自动识别程序
使用Playwright + 图像识别算法计算滑动距离
支持Chrome和Firefox浏览器
"""

import asyncio
import math
import os
import re
import ssl
import urllib.request
import json
import sys

import numpy as np
import cv2
from playwright.async_api import async_playwright

from image_captcha_solver import calculate_slide_distance


async def slide_drag_linear(page, center_x, center_y, distance):
    """匀速分段（原始方式）。"""
    current_x = 0.0
    step = max(5, int(distance) // 10)
    while current_x < distance:
        move_distance = min(step, distance - current_x)
        current_x += move_distance
        await page.mouse.move(center_x + current_x, center_y, steps=5)
        await asyncio.sleep(0.05)


async def slide_drag_ease_in_out_arc(page, center_x, center_y, distance):
    """缓入缓出 + 轻微弧线。"""
    def ease_in_out_cubic(t):
        if t <= 0:
            return 0.0
        if t >= 1:
            return 1.0
        if t < 0.5:
            return 4.0 * t * t * t
        return 1.0 - math.pow(-2.0 * t + 2.0, 3) / 2.0

    total_steps = max(28, min(72, max(12, int(distance) // 3)))
    prev_x = 0.0
    for i in range(1, total_steps + 1):
        t = i / total_steps
        eased = ease_in_out_cubic(t)
        target_x = distance * eased
        seg = target_x - prev_x
        prev_x = target_x
        arc_y = center_y + 2.0 * math.sin(t * math.pi)
        await page.mouse.move(
            center_x + target_x,
            arc_y,
            steps=max(2, min(12, int(abs(seg)) // 2 + 1)),
        )
        pace = 0.018 + 0.035 * (1.0 - abs(2.0 * t - 1.0))
        await asyncio.sleep(pace)


class TikTokCaptchaSolver:
    def __init__(
        self,
        download_dir="captcha_images",
        cookies_file="cookies.json",
        browser_type="chromium",
        slide_mode: str = "ease_arc",
    ):
        self.download_dir = download_dir
        self.cookies_file = cookies_file
        self.bg_image_path = os.path.join(download_dir, "background.jpg")
        self.slider_image_path = os.path.join(download_dir, "slider.png")
        self.browser_type = browser_type
        self.slide_mode = slide_mode
        os.makedirs(download_dir, exist_ok=True)
        
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE

    def download_image(self, url: str, save_path: str) -> bool:
        """下载图片"""
        try:
            print(f"正在下载: {url[:80]}...")
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            with urllib.request.urlopen(req, context=self.ctx, timeout=30) as response:
                with open(save_path, 'wb') as f:
                    f.write(response.read())
            print(f"图片已保存: {save_path}")
            return True
        except Exception as e:
            print(f"下载失败: {e}")
            return False

    def extract_image_urls_from_html(self, html_path: str) -> tuple:
        """从HTML文件中提取图片URL"""
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        bg_pattern = r'id="captcha-verify-image"[^>]+src="([^"]+)"'
        slider_pattern = r'class="[^"]*captcha_verify_img_slide[^"]*"[^>]*src="([^"]+)"'
        
        bg_match = re.search(bg_pattern, html_content)
        slider_match = re.search(slider_pattern, html_content)
        
        bg_url = bg_match.group(1) if bg_match else None
        slider_url = slider_match.group(1) if slider_match else None
        
        return bg_url, slider_url

    async def init_browser(self):
        """初始化Playwright浏览器"""
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
        
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        print(f"浏览器初始化完成: {self.browser_type}")

    async def open_captcha_page(self, url: str):
        """打开验证码页面"""
        print(f"正在打开页面: {url}")
        await self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
        print("等待页面加载...")
        await asyncio.sleep(5)
        await self.page.wait_for_load_state("networkidle", timeout=60000)
        await asyncio.sleep(5)
        print("页面加载完成")

    async def check_captcha_exists(self) -> bool:
        """检查验证码是否存在"""
        try:
            bg_locator = self.page.locator("#captcha-verify-image")
            slider_locator = self.page.locator(".captcha_verify_img_slide")
            
            await bg_locator.wait_for(state="attached", timeout=5000)
            await slider_locator.wait_for(state="attached", timeout=5000)
            
            bg_visible = await bg_locator.is_visible()
            slider_visible = await slider_locator.is_visible()
            
            return bg_visible and slider_visible
        except:
            return False

    async def get_captcha_images(self, html_path: str = None):
        """获取验证码图片"""
        print("正在获取验证码图片...")
        
        if html_path:
            bg_url, slider_url = self.extract_image_urls_from_html(html_path)
        else:
            bg_locator = self.page.locator("#captcha-verify-image")
            slider_locator = self.page.locator(".captcha_verify_img_slide")
            
            await bg_locator.wait_for(state="visible", timeout=10000)
            await slider_locator.wait_for(state="visible", timeout=10000)
            
            bg_url = await bg_locator.get_attribute("src")
            slider_url = await slider_locator.get_attribute("src")
        
        if bg_url:
            print(f"背景图URL: {bg_url[:100]}...")
            bg_success = self.download_image(bg_url, self.bg_image_path)
        else:
            print("未找到背景图URL")
            bg_success = False
        
        if slider_url:
            print(f"滑块图URL: {slider_url[:100]}...")
            slider_success = self.download_image(slider_url, self.slider_image_path)
        else:
            print("未找到滑块图URL")
            slider_success = False
        
        if not bg_success or not slider_success:
            print("图片下载失败，尝试使用Playwright截图...")
            await self._screenshot_captcha()
        
        return self.bg_image_path, self.slider_image_path

    async def _screenshot_captcha(self):
        """使用Playwright截图获取验证码图片"""
        bg_locator = self.page.locator("#captcha-verify-image")
        slider_locator = self.page.locator(".captcha_verify_img_slide")
        
        try:
            await bg_locator.wait_for(state="visible", timeout=5000)
            await slider_locator.wait_for(state="visible", timeout=5000)
            
            bg_bounding = await bg_locator.bounding_box()
            slider_bounding = await slider_locator.bounding_box()
            
            full_screenshot = await self.page.screenshot(full_page=False)
            full_img = np.frombuffer(full_screenshot, dtype=np.uint8)
            full_img = cv2.imdecode(full_img, cv2.IMREAD_COLOR)
            
            if bg_bounding:
                x, y, w, h = int(bg_bounding['x']), int(bg_bounding['y']), int(bg_bounding['width']), int(bg_bounding['height'])
                bg_crop = full_img[y:y+h, x:x+w]
                cv2.imwrite(self.bg_image_path, bg_crop)
                print(f"背景图已截图保存: {self.bg_image_path}")
            
            if slider_bounding:
                x, y, w, h = int(slider_bounding['x']), int(slider_bounding['y']), int(slider_bounding['width']), int(slider_bounding['height'])
                slider_crop = full_img[y:y+h, x:x+w]
                cv2.imwrite(self.slider_image_path, slider_crop)
                print(f"滑块图已截图保存: {self.slider_image_path}")
        except Exception as e:
            print(f"截图失败: {e}")

    def calculate_slide_distance(self) -> int:
        """调用图像识别算法计算滑动距离"""
        return calculate_slide_distance(
            self.bg_image_path, 
            self.slider_image_path,
            self.download_dir
        )

    async def scale_slide_distance_to_viewport(self, distance_image_px: int) -> int:
        """
        将 OpenCV 在下载图上的水平距离换算成页面 CSS 像素。
        页面上背景图往往比图片文件显示得更窄/更宽，不缩放会按比例拖过头或拖不够。
        """
        try:
            bg = self.page.locator("#captcha-verify-image")
            await bg.wait_for(state="visible", timeout=5000)
            box = await bg.bounding_box()
            natural_w = await bg.evaluate("el => el.naturalWidth || 0")
            if box and natural_w and natural_w > 0:
                scale = box["width"] / float(natural_w)
                out = int(round(distance_image_px * scale))
                print(
                    f"视口换算: 图像 {distance_image_px}px × 显示宽/自然宽 "
                    f"({box['width']:.1f}/{natural_w}) = {out}px"
                )
                return max(1, out)
        except Exception as e:
            print(f"视口换算失败，使用图像像素距离: {e}")
        try:
            img = cv2.imread(self.bg_image_path)
            if img is not None and img.shape[1] > 0:
                bg = self.page.locator("#captcha-verify-image")
                box = await bg.bounding_box()
                if box:
                    scale = box["width"] / float(img.shape[1])
                    out = int(round(distance_image_px * scale))
                    print(f"视口换算(本地图宽): {distance_image_px}px → {out}px")
                    return max(1, out)
        except Exception:
            pass
        return distance_image_px

    async def drag_slider(self, distance: int, slide_mode=None):
        """执行滑块拖拽。slide_mode: linear（默认）或 ease_arc；可传参覆盖构造时的 self.slide_mode。"""
        mode = slide_mode if slide_mode is not None else self.slide_mode
        
        try:
            slider_button = self.page.locator(".secsdk-captcha-drag-icon")
            
            await slider_button.wait_for(state="attached", timeout=15000)
            
            await asyncio.sleep(2)
            
            try:
                await slider_button.wait_for(state="visible", timeout=5000)
            except:
                print("等待滑块可见超时")
            
            await slider_button.scroll_into_view_if_needed()
            box = await slider_button.bounding_box()
            if box:
                distance = await self.scale_slide_distance_to_viewport(distance)
                print(f"正在拖拽滑块，距离: {distance}px，方式: {mode}")
                # Playwright 的 mouse.move(x,y) 为视口绝对坐标，不是相对位移；
                # 原先写成 move(current_x, 0) 会把鼠标拖到页面左上角，滑块不会动。
                center_x = box['x'] + box['width'] / 2
                center_y = box['y'] + box['height'] / 2
                
                await self.page.mouse.move(center_x, center_y)
                await asyncio.sleep(0.1)
                await self.page.mouse.down()

                if mode == "ease_arc":
                    await slide_drag_ease_in_out_arc(
                        self.page, center_x, center_y, float(distance)
                    )
                else:
                    await slide_drag_linear(
                        self.page, center_x, center_y, float(distance)
                    )

                await self.page.mouse.up()
                await asyncio.sleep(5)
                print("滑块拖拽完成")
            else:
                print("无法获取滑块位置")
        except Exception as e:
            print(f"拖拽失败: {e}")
            import traceback
            traceback.print_exc()
        
        await asyncio.sleep(5)
        
        try:
            success_locator = self.page.locator(".secsdk-captcha-drag-success")
            if await success_locator.count() > 0:
                print("验证成功！")
                return
            
            success_text = self.page.locator("text=验证成功")
            if await success_text.count() > 0:
                print("验证成功！")
                return
            
            print("等待验证结果...")
        except:
            pass

    async def save_cookies(self):
        """保存cookies到本地文件"""
        cookies = await self.context.cookies()
        with open(self.cookies_file, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
        print(f"Cookies已保存到: {self.cookies_file}")

    async def close(self):
        """关闭浏览器"""
        if hasattr(self, 'browser'):
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()


async def main(target_url: str, browser_type: str = "chromium"):
    solver = TikTokCaptchaSolver(browser_type=browser_type)
    
    try:
        await solver.init_browser()
        await solver.open_captcha_page(target_url)
        
        captcha_found = await solver.check_captcha_exists()
        
        if not captcha_found:
            print("未检测到验证码，验证码可能已经通过")
            await solver.save_cookies()
            print("\n=== 验证码已通过 ===")
            print(f"Cookies已保存到: {solver.cookies_file}")
            return
        
        await solver.get_captcha_images()
        
        distance = solver.calculate_slide_distance()
        
        await solver.drag_slider(distance)
        
        await asyncio.sleep(5)
        
        await solver.save_cookies()
        
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
    browser_type = sys.argv[1] if len(sys.argv) > 1 else "chromium"
    if browser_type not in ["chromium", "firefox"]:
        print("浏览器类型错误，支持: chromium, firefox")
        sys.exit(1)
    browser_type = 'chromium'
    target_url = "https://shop.tiktok.com/view/product/1731100904240220173?region=PH&locale=zh-CN&source=agency&fp=verify_mnl3n7cj_aSv30Dzf_EBfK_4dst_B2mn_oMGLkuFuZYU8"
    asyncio.run(main(target_url, browser_type))
