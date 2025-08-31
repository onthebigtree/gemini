#!/usr/bin/env python3
"""
最终测试 - 验证可选文件上传修复
"""

import requests
import io
from PIL import Image

BASE_URL = "http://localhost:8000"

def test_text_only():
    """测试纯文本生成 - 完全不传image字段"""
    print("🧪 测试1: 纯文本生成（不传image字段）")
    
    data = {"prompt": "你好，请说一句话"}
    
    try:
        response = requests.post(f"{BASE_URL}/generate", data=data)
        print(f"  状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"  ✅ 成功! 消息: {result.get('message', '')}")
            print(f"  模式: {'纯文本' if '纯文本' in result.get('message', '') else '未知'}")
            return True
        else:
            print(f"  ❌ 失败: {response.text}")
            return False
            
    except Exception as e:
        print(f"  ❌ 请求错误: {e}")
        return False

def test_empty_image():
    """测试传空的image字段"""
    print("\n🧪 测试2: 传空的image字段")
    
    data = {"prompt": "你好，请说一句话", "image": ""}
    
    try:
        response = requests.post(f"{BASE_URL}/generate", data=data)
        print(f"  状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"  ✅ 成功! 消息: {result.get('message', '')}")
            return True
        else:
            print(f"  ❌ 失败: {response.text}")
            return False
            
    except Exception as e:
        print(f"  ❌ 请求错误: {e}")
        return False

def test_with_image():
    """测试图文混合生成"""
    print("\n🧪 测试3: 图文混合生成")
    
    # 创建一个简单的测试图片
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    data = {"prompt": "描述这张图片"}
    files = {"image": ("test.png", img_bytes, "image/png")}
    
    try:
        response = requests.post(f"{BASE_URL}/generate", data=data, files=files)
        print(f"  状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"  ✅ 成功! 消息: {result.get('message', '')}")
            print(f"  模式: {'图文混合' if '图文混合' in result.get('message', '') else '未知'}")
            return True
        else:
            print(f"  ❌ 失败: {response.text}")
            return False
            
    except Exception as e:
        print(f"  ❌ 请求错误: {e}")
        return False

def test_missing_prompt():
    """测试缺少prompt参数"""
    print("\n🧪 测试4: 缺少prompt参数")
    
    data = {"model": "test"}
    
    try:
        response = requests.post(f"{BASE_URL}/generate", data=data)
        print(f"  状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if not result.get('success', True):
                print(f"  ✅ 正确处理错误: {result.get('message', '')}")
                return True
            else:
                print(f"  ❌ 应该返回错误但没有")
                return False
        else:
            print(f"  ❌ 状态码错误: {response.text}")
            return False
            
    except Exception as e:
        print(f"  ❌ 请求错误: {e}")
        return False

if __name__ == "__main__":
    print("🚀 开始最终测试...")
    print("=" * 50)
    
    tests = [
        ("纯文本生成", test_text_only),
        ("空image字段", test_empty_image), 
        ("图文混合", test_with_image),
        ("参数验证", test_missing_prompt)
    ]
    
    results = []
    for test_name, test_func in tests:
        result = test_func()
        results.append((test_name, result))
    
    print("\n" + "=" * 50)
    print("📊 测试结果汇总:")
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 所有测试通过！可选文件上传问题已彻底解决！")
    else:
        print("⚠️ 部分测试失败，需要进一步检查")
