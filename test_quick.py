#!/usr/bin/env python3
"""
快速测试元组/列表修复
"""

import requests

def test_empty_image():
    """测试空 image 字段"""
    print("🧪 测试空 image 字段...")
    
    data = {
        'prompt': 'gen a bot',
        'model': '',
        'image': ''
    }
    
    try:
        response = requests.post("http://127.0.0.1:8000/generate", data=data, timeout=10)
        print(f"📥 状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 成功! 消息: {result.get('message', '')}")
            print(f"✅ 成功字段: {result.get('success', False)}")
            return True
        else:
            print(f"❌ 失败: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

if __name__ == "__main__":
    print("🚀 快速测试元组/列表修复...")
    print("=" * 40)
    
    success = test_empty_image()
    
    print("\n" + "=" * 40)
    if success:
        print("🎉 修复成功！")
        print("✅ 异常处理器现在能正确识别 image 字段错误")
    else:
        print("💩 还是有问题...")
        
    print(f"\n结果: {'成功' if success else '失败'}")
