"""
图片相似度计算服务

使用感知哈希(pHash) + 直方图对比的组合策略，快速判断两张商品图片是否相似。
适用于拍照购结果与 TikTok 商品主图的匹配验证。
"""
import hashlib
import logging
import os
import ssl
import tempfile
from typing import Optional, Tuple

import cv2
import numpy as np
import httpx
from PIL import Image

logger = logging.getLogger(__name__)

# 相似度阈值（0~1），高于此值认为两张图片匹配
DEFAULT_SIMILARITY_THRESHOLD = 0.75

# pHash 权重 vs 直方图权重
PHASH_WEIGHT = 0.6
HISTOGRAM_WEIGHT = 0.4

# TikTok 图片域名列表，需要特殊处理 SSL
TIKTOK_IMAGE_DOMAINS = [
    "p16-oec-sg.ibyteimg.com",
    "p16-oec-va.ibyteimg.com",
    "p16-oec-common-useast2a.ibyteimg.com",
    "p16-shop-sg.ibyteimg.com",
    "p16-sign-sg.tiktokcdn.com",
    "p16-sign-va.tiktokcdn.com",
]


def _is_tiktok_image(url: str) -> bool:
    """判断是否为 TikTok 图片 URL"""
    return any(domain in url for domain in TIKTOK_IMAGE_DOMAINS)


def _download_image(url: str, timeout: int = 15) -> Optional[bytes]:
    """从 URL 下载图片二进制数据"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.tiktok.com/",
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
        }

        # TikTok 图片服务器需要禁用 SSL 验证
        verify_ssl = not _is_tiktok_image(url)

        with httpx.Client(verify=verify_ssl, timeout=timeout) as client:
            resp = client.get(url, headers=headers, follow_redirects=True)
            resp.raise_for_status()
            return resp.content
    except Exception as e:
        logger.warning("Failed to download image from %s: %s", url[:100], e)
        return None


def _bytes_to_cv2_image(data: bytes) -> Optional[np.ndarray]:
    """将二进制图片数据转为 OpenCV numpy 数组"""
    try:
        nparr = np.frombuffer(data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img
    except Exception as e:
        logger.warning("Failed to decode image: %s", e)
        return None


def _compute_phash(img: np.ndarray, hash_size: int = 16) -> np.ndarray:
    """
    计算感知哈希(pHash)。
    基于 DCT(离散余弦变换) 的低频特征，对缩放、亮度变化、轻微裁剪鲁棒。
    返回 hash_size x hash_size 的二值矩阵。
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA)
    resized_float = np.float32(resized) - 128.0

    dct = cv2.dct(resized_float)
    dct_low_freq = dct[:hash_size, :hash_size]

    median = np.median(dct_low_freq)
    phash = (dct_low_freq > median).astype(np.uint8)
    return phash


def _hamming_distance(hash1: np.ndarray, hash2: np.ndarray) -> float:
    """计算两个 pHash 的汉明距离，返回相似度 (0~1)"""
    total_bits = hash1.size
    diff = np.sum(hash1 != hash2)
    return 1.0 - (diff / total_bits)


def _compute_histogram_similarity(img1: np.ndarray, img2: np.ndarray) -> float:
    """
    计算两张图片的 HSV 颜色直方图相似度。
    使用相关性对比，返回 0~1 的值。
    """
    hsv1 = cv2.cvtColor(img1, cv2.COLOR_BGR2HSV)
    hsv2 = cv2.cvtColor(img2, cv2.COLOR_BGR2HSV)

    hist1 = cv2.calcHist([hsv1], [0, 1], None, [50, 60], [0, 180, 0, 256])
    hist2 = cv2.calcHist([hsv2], [0, 1], None, [50, 60], [0, 180, 0, 256])

    cv2.normalize(hist1, hist1)
    cv2.normalize(hist2, hist2)

    similarity = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
    return max(0.0, similarity)


def _compute_sift_similarity(img1: np.ndarray, img2: np.ndarray) -> float:
    """
    使用 SIFT 特征点匹配计算相似度。
    对旋转、缩放、视角变化鲁棒，但计算成本较高。
    返回匹配点比例 (0~1)。
    """
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

    sift = cv2.SIFT_create()
    kp1, des1 = sift.detectAndCompute(gray1, None)
    kp2, des2 = sift.detectAndCompute(gray2, None)

    if des1 is None or des2 is None or len(kp1) < 4 or len(kp2) < 4:
        return 0.0

    bf = cv2.BFMatcher()
    matches = bf.knnMatch(des1, des2, k=2)

    good_matches = []
    for m, n in matches:
        if m.distance < 0.7 * n.distance:
            good_matches.append(m)

    min_keypoints = min(len(kp1), len(kp2))
    if min_keypoints == 0:
        return 0.0

    return min(len(good_matches) / min_keypoints, 1.0)


def calculate_image_similarity(
    url1: str,
    url2: str,
    use_sift: bool = False,
) -> Optional[float]:
    """
    计算两张图片的综合相似度。

    Args:
        url1: 第一张图片 URL (如 TikTok 商品主图)
        url2: 第二张图片 URL (如 PDD 匹配商品图)
        use_sift: 是否启用 SIFT 特征匹配（更准确但更慢）

    Returns:
        相似度分数 (0~1)，失败返回 None
    """
    logger.info("Calculating image similarity: url1=%s, url2=%s", url1[:80], url2[:80])

    data1 = _download_image(url1)
    if not data1:
        logger.warning("Failed to download image 1: %s", url1[:80])
        return None

    data2 = _download_image(url2)
    if not data2:
        logger.warning("Failed to download image 2: %s", url2[:80])
        return None

    img1 = _bytes_to_cv2_image(data1)
    if img1 is None:
        logger.warning("Failed to decode image 1: %s", url1[:80])
        return None

    img2 = _bytes_to_cv2_image(data2)
    if img2 is None:
        logger.warning("Failed to decode image 2: %s", url2[:80])
        return None

    try:
        phash_sim = _hamming_distance(_compute_phash(img1), _compute_phash(img2))
        hist_sim = _compute_histogram_similarity(img1, img2)

        combined_score = PHASH_WEIGHT * phash_sim + HISTOGRAM_WEIGHT * hist_sim

        if use_sift:
            sift_sim = _compute_sift_similarity(img1, img2)
            combined_score = 0.4 * phash_sim + 0.3 * hist_sim + 0.3 * sift_sim

        logger.info(
            "Image similarity calculated: pHash=%.4f, hist=%.4f, combined=%.4f",
            phash_sim, hist_sim, combined_score,
        )

        return round(combined_score, 4)
    except Exception as e:
        logger.error("Error calculating image similarity: %s", e, exc_info=True)
        return None


def calculate_similarity_from_local(
    path1: str,
    path2: str,
    use_sift: bool = False,
) -> Optional[float]:
    """
    从本地文件路径计算图片相似度。

    Args:
        path1: 第一张图片本地路径
        path2: 第二张图片本地路径
        use_sift: 是否启用 SIFT 特征匹配

    Returns:
        相似度分数 (0~1)，失败返回 None
    """
    if not os.path.exists(path1) or not os.path.exists(path2):
        logger.warning("Image file not found: %s or %s", path1, path2)
        return None

    img1 = cv2.imread(path1)
    img2 = cv2.imread(path2)

    if img1 is None or img2 is None:
        return None

    phash_sim = _hamming_distance(_compute_phash(img1), _compute_phash(img2))
    hist_sim = _compute_histogram_similarity(img1, img2)

    combined_score = PHASH_WEIGHT * phash_sim + HISTOGRAM_WEIGHT * hist_sim

    if use_sift:
        sift_sim = _compute_sift_similarity(img1, img2)
        combined_score = 0.4 * phash_sim + 0.3 * hist_sim + 0.3 * sift_sim

    logger.debug(
        "Local image similarity: pHash=%.4f, hist=%.4f, combined=%.4f",
        phash_sim, hist_sim, combined_score,
    )

    return round(combined_score, 4)


def is_similar(
    url1: str,
    url2: str,
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> Tuple[bool, Optional[float]]:
    """
    判断两张图片是否相似。

    Args:
        url1: 第一张图片 URL
        url2: 第二张图片 URL
        threshold: 相似度阈值 (0~1)

    Returns:
        (是否相似, 相似度分数)
    """
    score = calculate_image_similarity(url1, url2)
    if score is None:
        return False, None
    return score >= threshold, score


def extract_main_image_from_screenshot(
    screenshot_path: str,
    image_bounds: tuple,
    output_path: str = None,
) -> Optional[str]:
    """
    从截图中根据坐标裁剪出商品主图。

    Args:
        screenshot_path: 结果页截图路径
        image_bounds: 图片在截图中的坐标 (x1, y1, x2, y2)
        output_path: 输出裁剪图片路径，None 则自动生成临时文件

    Returns:
        裁剪后的图片路径
    """
    if not os.path.exists(screenshot_path):
        return None

    img = cv2.imread(screenshot_path)
    if img is None:
        return None

    x1, y1, x2, y2 = image_bounds
    cropped = img[y1:y2, x1:x2]

    if cropped.size == 0:
        return None

    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix=".jpg", prefix="cropped_")
        os.close(fd)

    cv2.imwrite(output_path, cropped)
    logger.debug("Cropped image saved to %s", output_path)
    return output_path
