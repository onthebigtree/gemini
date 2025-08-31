#!/usr/bin/env python3
"""
测试 /generate 接口的可选文件上传功能
"""

import requests

BASE_URL = "http://localhost:8000"

def test_text_only():
    """测试纯文本生成"""
    print("🧪 测试纯文本生成...")
    
    data = {
        "prompt": "写一首关于春天的短诗"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/generate", data=data)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

def test_with_image():
    """测试图文混合生成"""
    print("\n🧪 测试图文混合生成...")
    
    data = {
        "prompt": "描述这张图片"
    }
    
    # 创建一个简单的测试图片
    import io
    from PIL import Image
    
    # 创建一个简单的红色方块图片
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    files = {
        "image": ("test.png", img_bytes, "image/png")
    }
    
    try:
        response = requests.post(f"{BASE_URL}/generate", data=data, files=files)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

if __name__ == "__main__":
    print("🚀 开始测试 /generate 接口...")
    
    # 测试纯文本
    text_ok = test_text_only()
    
    # 测试图文混合
    image_ok = test_with_image()
    
    print(f"\n📊 测试结果:")
    print(f"纯文本生成: {'✅ 通过' if text_ok else '❌ 失败'}")
    print(f"图文混合生成: {'✅ 通过' if image_ok else '❌ 失败'}")
    
    if text_ok and image_ok:
        print("\n🎉 所有测试通过！")
    else:
        print("\n⚠️  部分测试失败，请检查服务器状态")
