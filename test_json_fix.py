#!/usr/bin/env python3
"""
测试 JSON 序列化修复
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_empty_image_field():
    """测试空 image 字段，确保不会有 JSON 序列化错误"""
    print("🧪 测试空 image 字段的 JSON 序列化...")
    
    data = {
        'prompt': 'hello world',
        'model': '',
        'image': ''  # 这会触发验证错误和异常处理器
    }
    
    try:
        response = requests.post(f"{BASE_URL}/generate", data=data, timeout=10)
        print(f"  状态码: {response.status_code}")
        print(f"  响应头: {response.headers.get('content-type', 'unknown')}")
        
        # 检查是否能正确解析 JSON
        try:
            result = response.json()
            print(f"  ✅ JSON 解析成功!")
            print(f"  响应类型: {type(result)}")
            print(f"  成功字段: {result.get('success', 'N/A')}")
            print(f"  消息: {result.get('message', 'N/A')}")
            return True
        except json.JSONDecodeError as e:
            print(f"  ❌ JSON 解析失败: {e}")
            print(f"  原始响应: {response.text[:200]}...")
            return False
            
    except requests.exceptions.Timeout:
        print("  ❌ 请求超时")
        return False
    except Exception as e:
        print(f"  ❌ 请求错误: {e}")
        return False

def test_normal_request():
    """测试正常请求作为对比"""
    print("\n🧪 测试正常请求...")
    
    data = {'prompt': 'hello world'}
    
    try:
        response = requests.post(f"{BASE_URL}/generate", data=data, timeout=10)
        print(f"  状态码: {response.status_code}")
        
        try:
            result = response.json()
            print(f"  ✅ 正常请求 JSON 解析成功!")
            print(f"  成功字段: {result.get('success', 'N/A')}")
            return True
        except json.JSONDecodeError as e:
            print(f"  ❌ 正常请求 JSON 解析失败: {e}")
            return False
            
    except Exception as e:
        print(f"  ❌ 正常请求错误: {e}")
        return False

def test_server_health():
    """测试服务器健康状态"""
    print("\n🧪 测试服务器健康状态...")
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"  健康检查状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"  ✅ 服务器健康: {result}")
            return True
        else:
            print(f"  ❌ 服务器不健康: {response.text}")
            return False
            
    except Exception as e:
        print(f"  ❌ 健康检查失败: {e}")
        return False

if __name__ == "__main__":
    print("🚀 测试 JSON 序列化修复...")
    print("=" * 50)
    
    # 先检查服务器是否运行
    health_ok = test_server_health()
    
    if not health_ok:
        print("\n❌ 服务器未运行或不健康，请先启动服务器")
        print("运行命令: uvicorn main:app --reload")
        exit(1)
    
    # 运行测试
    tests = [
        ("空image字段", test_empty_image_field),
        ("正常请求", test_normal_request)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"  ❌ 测试异常: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📊 测试结果:")
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 JSON 序列化修复成功!")
        print("✅ 异常处理器工作正常")
        print("✅ 不会再有 JSON 序列化错误")
        print("✅ curl -F 'image=' 现在应该能正常工作")
    else:
        print("💩 还是有问题，需要继续调试...")
        
    print(f"\n🏆 修复状态: {'完全修复' if all_passed else '仍需改进'}")
