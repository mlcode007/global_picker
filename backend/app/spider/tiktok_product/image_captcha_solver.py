#!/usr/bin/env python3
"""
图像识别算法：计算滑块验证码滑动距离
使用OpenCV模板匹配算法
"""

import cv2
import numpy as np
import os


def calculate_slide_distance(bg_image_path: str, slider_image_path: str, 
                             output_dir: str = ".") -> int:
    """
    使用图像识别算法计算滑块滑动距离
    使用边缘检测 + 模板匹配方法
    
    Args:
        bg_image_path: 背景图路径
        slider_image_path: 滑块图路径
        output_dir: 输出目录，用于保存匹配结果图
    
    Returns:
        int: 滑动距离（像素）
    """
    print("正在计算滑动距离...")
    
    if not os.path.exists(bg_image_path):
        raise Exception(f"背景图不存在: {bg_image_path}")
    if not os.path.exists(slider_image_path):
        raise Exception(f"滑块图不存在: {slider_image_path}")
    
    bg_img = cv2.imread(bg_image_path)
    slider_img = cv2.imread(slider_image_path)
    
    if bg_img is None:
        raise Exception(f"无法读取背景图: {bg_image_path}")
    if slider_img is None:
        raise Exception(f"无法读取滑块图: {slider_image_path}")
    
    bg_gray = cv2.cvtColor(bg_img, cv2.COLOR_BGR2GRAY)
    slider_gray = cv2.cvtColor(slider_img, cv2.COLOR_BGR2GRAY)
    
    slider_height, slider_width = slider_gray.shape
    print(f"滑块尺寸: {slider_width}x{slider_height}")
    
    bg_height, bg_width = bg_gray.shape
    print(f"背景图尺寸: {bg_width}x{bg_height}")
    
    bg_edges = cv2.Canny(bg_gray, 50, 150)
    slider_edges = cv2.Canny(slider_gray, 50, 150)
    
    res = cv2.matchTemplate(bg_edges, slider_edges, cv2.TM_CCOEFF_NORMED)
    # 边缘匹配置信度往往低于灰度；阈值过高会误用灰度全局最大值（容易贴到错误纹理）
    edge_threshold = 0.18
    _min_e, max_e, _min_loc_e, max_loc_e = cv2.minMaxLoc(res)
    
    if max_e >= edge_threshold:
        best_match_x, best_match_y = max_loc_e[0], max_loc_e[1]
        best_match_val = max_e
        distance = best_match_x
        print(f"使用边缘匹配结果: {distance}px, 置信度: {best_match_val}")
        best_loc = (best_match_x, best_match_y)
    else:
        res2 = cv2.matchTemplate(bg_gray, slider_gray, cv2.TM_CCOEFF_NORMED)
        min_val2, max_val2, min_loc2, max_loc2 = cv2.minMaxLoc(res2)
        
        if max_val2 > 0.3:
            distance = max_loc2[0]
            print(f"使用灰度匹配结果: {distance}px, 置信度: {max_val2}")
            best_loc = max_loc2
        else:
            distance = 0
            best_loc = (0, 0)
            print(f"匹配失败，使用默认值: {distance}px")
    
    matched_img = bg_img.copy()
    cv2.rectangle(matched_img, best_loc, 
                 (best_loc[0] + slider_width, best_loc[1] + slider_height),
                 (0, 255, 0), 2)
    
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "matched_result.jpg")
    cv2.imwrite(output_path, matched_img)
    print(f"匹配结果已保存: {output_path}")
    
    print(f"计算出的滑动距离: {distance}px")
    return distance


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("用法: python3 image_captcha_solver.py <背景图路径> <滑块图路径> [输出目录]")
        print("示例: python3 image_captcha_solver.py background.jpg slider.png ./output")
        sys.exit(1)
    
    bg_path = sys.argv[1]
    slider_path = sys.argv[2]
    output_dir = sys.argv[3] if len(sys.argv) > 3 else "."
    
    distance = calculate_slide_distance(bg_path, slider_path, output_dir)
    print(f"\n=== 验证码处理完成 ===")
    print(f"滑动距离: {distance}px")
