"""
图片相似度功能测试脚本

用法：
    # 测试两张URL图片的相似度
    python backend/scripts/test_image_similarity.py --url1 "https://example.com/img1.jpg" --url2 "https://example.com/img2.jpg"
    
    # 测试两张本地图片的相似度
    python backend/scripts/test_image_similarity.py --path1 "/path/to/img1.jpg" --path2 "/path/to/img2.jpg"
    
    # 启用SIFT特征匹配（更准确但更慢）
    python backend/scripts/test_image_similarity.py --url1 "..." --url2 "..." --use-sift
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.image_similarity_service import (
    calculate_image_similarity,
    calculate_similarity_from_local,
    is_similar,
    DEFAULT_SIMILARITY_THRESHOLD,
)


def test_urls(url1: str, url2: str, use_sift: bool = False):
    """测试两个URL图片的相似度"""
    print(f"Testing URL similarity...")
    print(f"URL1: {url1}")
    print(f"URL2: {url2}")
    print()
    
    score = calculate_image_similarity(url1, url2, use_sift=use_sift)
    
    if score is None:
        print("Failed to calculate similarity (download or decode error)")
        return
    
    similar, _ = is_similar(url1, url2, DEFAULT_SIMILARITY_THRESHOLD)
    
    print(f"Similarity Score: {score:.4f}")
    print(f"Threshold: {DEFAULT_SIMILARITY_THRESHOLD}")
    print(f"Is Similar: {'Yes' if similar else 'No'}")


def test_paths(path1: str, path2: str, use_sift: bool = False):
    """测试两个本地图片的相似度"""
    print(f"Testing local image similarity...")
    print(f"Path1: {path1}")
    print(f"Path2: {path2}")
    print()
    
    if not os.path.exists(path1):
        print(f"Error: File not found: {path1}")
        return
    if not os.path.exists(path2):
        print(f"Error: File not found: {path2}")
        return
    
    score = calculate_similarity_from_local(path1, path2, use_sift=use_sift)
    
    if score is None:
        print("Failed to calculate similarity (decode error)")
        return
    
    print(f"Similarity Score: {score:.4f}")
    print(f"Threshold: {DEFAULT_SIMILARITY_THRESHOLD}")
    print(f"Is Similar: {'Yes' if score >= DEFAULT_SIMILARITY_THRESHOLD else 'No'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test image similarity calculation")
    parser.add_argument("--url1", help="First image URL")
    parser.add_argument("--url2", help="Second image URL")
    parser.add_argument("--path1", help="First image local path")
    parser.add_argument("--path2", help="Second image local path")
    parser.add_argument("--use-sift", action="store_true", help="Enable SIFT feature matching (slower but more accurate)")
    
    args = parser.parse_args()
    
    if args.url1 and args.url2:
        test_urls(args.url1, args.url2, args.use_sift)
    elif args.path1 and args.path2:
        test_paths(args.path1, args.path2, args.use_sift)
    else:
        parser.print_help()
        print("\nError: Please provide either --url1/--url2 or --path1/--path2")
        sys.exit(1)
