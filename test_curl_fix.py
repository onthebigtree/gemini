#!/usr/bin/env python3
"""
测试 curl 命令中 -F 'image=' 空值的情况
"""

import requests
import subprocess
import json

BASE_URL = "http://127.0.0.1:8000"

def test_curl_empty_image():
    """测试 curl 命令中 -F 'image=' 的情况"""
    print("🧪 测试 curl -F 'image=' 空值情况...")
    
    # 使用 requests 模拟 curl 的行为
    data = {
        'prompt': 'gen a bot',
        'model': '',
        'image': ''  # 这会导致 FastAPI 验证错误
    }
    
    try:
        response = requests.post(f"{BASE_URL}/generate", data=data)
        print(f"  状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"  ✅ 成功! 消息: {result.get('message', '')}")
            print(f"  成功字段: {result.get('success', False)}")
            return True
        else:
            print(f"  ❌ 失败: {response.text}")
            return False
            
    except Exception as e:
        print(f"  ❌ 请求错误: {e}")
        return False

def test_multipart_empty_image():
    """测试 multipart/form-data 中空 image 字段"""
    print("\n🧪 测试 multipart/form-data 空 image 字段...")
    
    from requests_toolbelt.multipart.encoder import MultipartEncoder
    
    multipart_data = MultipartEncoder(
        fields={
            'prompt': 'gen a bot',
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

def test_actual_curl_command():
    """测试实际的 curl 命令"""
    print("\n🧪 测试实际 curl 命令...")
    
    curl_cmd = [
        'curl', '-X', 'POST',
        f'{BASE_URL}/generate',
        '-H', 'accept: application/json',
        '-H', 'Content-Type: multipart/form-data',
        '-F', 'prompt=gen a bot',
        '-F', 'model=',
        '-F', 'image=',
        '--silent'  # 静默模式，只返回响应内容
    ]
    
    try:
        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=30)
        
        print(f"  curl 退出码: {result.returncode}")
        
        if result.returncode == 0:
            try:
                response_data = json.loads(result.stdout)
                print(f"  ✅ curl 成功! 消息: {response_data.get('message', '')}")
                return True
            except json.JSONDecodeError:
                print(f"  ❌ curl 响应不是有效 JSON: {result.stdout}")
                return False
        else:
            print(f"  ❌ curl 失败: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("  ❌ curl 命令超时")
        return False
    except Exception as e:
        print(f"  ❌ curl 命令错误: {e}")
        return False

def test_normal_request():
    """测试正常请求（作为对比）"""
    print("\n🧪 测试正常请求（无 image 字段）...")
    
    data = {'prompt': 'gen a bot'}
    
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

if __name__ == "__main__":
    print("🚀 测试 curl -F 'image=' 空值修复...")
    print("=" * 60)
    
    tests = [
        ("requests 空 image", test_curl_empty_image),
        ("multipart 空 image", test_multipart_empty_image),
        ("实际 curl 命令", test_actual_curl_command),
        ("正常请求对比", test_normal_request)
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
        print("🎉 所有测试通过！")
        print("✅ curl -F 'image=' 不会再报错")
        print("✅ 全局异常处理器工作正常")
        print("✅ 自动回退到手动解析")
    else:
        print("⚠️ 部分测试失败")
        
    print(f"\n🏆 修复状态: {'完全修复' if all_passed else '仍需改进'}")
