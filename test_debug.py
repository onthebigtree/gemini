#!/usr/bin/env python3
"""
调试测试 - 检查异常处理器是否被触发
"""

import requests
import time

BASE_URL = "http://127.0.0.1:8000"

def test_curl_simulation():
    """模拟 curl 请求"""
    print("🧪 模拟 curl -F 'image=' 请求...")
    
    data = {
        'prompt': 'gen a bot',
        'model': '',
        'image': ''  # 这应该触发验证错误
    }
    
    print(f"📤 发送请求到: {BASE_URL}/generate")
    print(f"📤 请求数据: {data}")
    
    try:
        response = requests.post(f"{BASE_URL}/generate", data=data, timeout=10)
        print(f"📥 响应状态码: {response.status_code}")
        print(f"📥 响应头: {dict(response.headers)}")
        print(f"📥 响应内容: {response.text}")
        
        # 检查是否是我们期望的成功响应
        if response.status_code == 200:
            try:
                result = response.json()
                if result.get('success'):
                    print("✅ 异常处理器工作正常！")
                    return True
                else:
                    print(f"⚠️ 请求被处理但返回失败: {result.get('message')}")
                    return False
            except:
                print("❌ 响应不是有效的 JSON")
                return False
        else:
            print("❌ 仍然返回错误状态码")
            return False
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False

if __name__ == "__main__":
    print("🚀 调试异常处理器...")
    print("=" * 50)
    print("⚠️ 请确保服务器正在运行并查看服务器日志")
    print("⚠️ 应该能看到 '🚨 异常处理器被触发!' 的日志")
    print("=" * 50)
    
    # 等待一下确保服务器准备好
    time.sleep(1)
    
    success = test_curl_simulation()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 异常处理器工作正常！")
        print("✅ curl -F 'image=' 应该能正常工作")
    else:
        print("💩 异常处理器没有被触发或工作不正常")
        print("🔍 请检查服务器日志中是否有调试信息")
        print("🔍 如果没有看到 '🚨 异常处理器被触发!'，说明异常处理器没有被注册成功")
    
    print(f"\n📝 测试结果: {'成功' if success else '失败'}")
    print("\n💡 提示: 重启服务器后再试一次")
    print("💡 命令: uvicorn main:app --reload")
