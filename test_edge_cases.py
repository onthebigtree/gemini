#!/usr/bin/env python3
"""
测试所有边界情况，确保 image= 空值不会报错
"""

import requests
import io
from PIL import Image

BASE_URL = "http://localhost:8000"

def test_no_image_field():
    """测试1: 完全不传 image 字段"""
    print("🧪 测试1: 不传 image 字段")
    
    data = {"prompt": "你好"}
    
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

def test_empty_image_field():
    """测试2: 传空的 image 字段"""
    print("\n🧪 测试2: 传空的 image 字段 (image='')")
    
    data = {"prompt": "你好", "image": ""}
    
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

def test_none_image_field():
    """测试3: 传 None 的 image 字段"""
    print("\n🧪 测试3: 传 None 的 image 字段")
    
    data = {"prompt": "你好", "image": None}
    
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

def test_empty_file_upload():
    """测试4: 上传空文件名的文件"""
    print("\n🧪 测试4: 上传空文件名的文件")
    
    data = {"prompt": "你好"}
    files = {"image": ("", io.BytesIO(b""), "application/octet-stream")}
    
    try:
        response = requests.post(f"{BASE_URL}/generate", data=data, files=files)
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

def test_valid_image_upload():
    """测试5: 上传有效图片"""
    print("\n🧪 测试5: 上传有效图片")
    
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
            return True
        else:
            print(f"  ❌ 失败: {response.text}")
            return False
            
    except Exception as e:
        print(f"  ❌ 请求错误: {e}")
        return False

def test_multipart_form_simulation():
    """测试6: 模拟 Swagger UI 的 multipart/form-data 请求"""
    print("\n🧪 测试6: 模拟 Swagger UI 的空 image 字段")
    
    # 模拟 Swagger UI 发送的请求格式
    import requests
    from requests_toolbelt.multipart.encoder import MultipartEncoder
    
    multipart_data = MultipartEncoder(
        fields={
            'prompt': '你好，请说一句话',
            'model': '',
            'image': ('', '', 'application/octet-stream')  # 空文件
        }
    )
    
    try:
        response = requests.post(
            f"{BASE_URL}/generate",
            data=multipart_data,
            headers={'Content-Type': multipart_data.content_type}
        )
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

if __name__ == "__main__":
    print("🚀 开始边界情况测试...")
    print("=" * 60)
    
    tests = [
        ("不传image字段", test_no_image_field),
        ("空image字段", test_empty_image_field),
        ("None image字段", test_none_image_field),
        ("空文件上传", test_empty_file_upload),
        ("有效图片上传", test_valid_image_upload),
        ("Swagger UI模拟", test_multipart_form_simulation)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"  ❌ 测试异常: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 60)
    print("📊 测试结果汇总:")
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有边界情况测试通过！")
        print("✅ image= 空值不会再报错")
        print("✅ 智能识别纯文本和图文混合模式")
        print("✅ 兼容 Swagger UI 的各种请求格式")
    else:
        print("⚠️ 部分测试失败，需要进一步检查")
        
    print(f"\n📝 总结: {sum(1 for _, passed in results if passed)}/{len(results)} 个测试通过")
