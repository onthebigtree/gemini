#!/usr/bin/env python3
"""
简单测试 /generate 接口的纯文本功能
"""

import requests

def test_text_only():
    """测试纯文本生成 - 不传 image 字段"""
    print("🧪 测试纯文本生成（不传image字段）...")
    
    # 只传 prompt，不传 image
    data = {
        "prompt": "你好，请说一句话"
    }
    
    try:
        response = requests.post("http://localhost:8000/generate", data=data)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 成功! 响应: {result}")
            return True
        else:
            print(f"❌ 失败! 响应: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 请求错误: {e}")
        return False

if __name__ == "__main__":
    print("🚀 测试不传图片的情况...")
    success = test_text_only()
    
    if success:
        print("\n🎉 测试通过！可选文件上传修复成功！")
    else:
        print("\n⚠️ 测试失败，请检查修复")
