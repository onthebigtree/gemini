#!/usr/bin/env python3
"""
测试 Swagger UI 参数是否恢复显示
"""

import requests
import json

def check_swagger_ui_params():
    """检查 Swagger UI 是否能看到所有参数"""
    print("🔍 检查 Swagger UI 参数显示...")
    
    try:
        response = requests.get("http://localhost:8000/openapi.json")
        if response.status_code != 200:
            print(f"❌ 无法获取 OpenAPI schema: {response.status_code}")
            return False
            
        schema = response.json()
        
        # 查找 /generate 端点
        generate_path = schema.get("paths", {}).get("/generate", {})
        post_method = generate_path.get("post", {})
        request_body = post_method.get("requestBody", {})
        
        if not request_body:
            print("❌ 没有 Request Body！")
            return False
            
        content = request_body.get("content", {})
        form_data = content.get("multipart/form-data", {})
        
        if not form_data:
            print("❌ 没有 multipart/form-data 支持！")
            return False
            
        properties = form_data.get("schema", {}).get("properties", {})
        required = form_data.get("schema", {}).get("required", [])
        
        print(f"\n📋 Swagger UI 中可见的参数:")
        for param_name, param_info in properties.items():
            param_type = param_info.get("type", "unknown")
            param_format = param_info.get("format", "")
            is_required = param_name in required
            description = param_info.get("description", "")
            
            print(f"  ✅ {param_name}: {param_type} {param_format} {'(必填)' if is_required else '(可选)'}")
            if description:
                print(f"      描述: {description}")
        
        # 检查必要参数
        expected_params = ["prompt", "model", "image"]
        missing_params = [p for p in expected_params if p not in properties]
        
        if missing_params:
            print(f"\n❌ 缺少参数: {missing_params}")
            return False
        else:
            print(f"\n✅ 所有参数都在 Swagger UI 中可见！")
            return True
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

def test_functionality():
    """测试功能是否正常"""
    print("\n🧪 测试基本功能...")
    
    # 测试纯文本
    data = {"prompt": "你好"}
    
    try:
        response = requests.post("http://localhost:8000/generate", data=data)
        print(f"  纯文本测试 - 状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"  ✅ 纯文本测试成功: {result.get('message', '')}")
            return True
        else:
            print(f"  ❌ 纯文本测试失败: {response.text}")
            return False
            
    except Exception as e:
        print(f"  ❌ 功能测试错误: {e}")
        return False

if __name__ == "__main__":
    print("🚀 检查 Swagger UI 是否恢复正常...")
    print("=" * 50)
    
    swagger_ok = check_swagger_ui_params()
    function_ok = test_functionality()
    
    print("\n" + "=" * 50)
    print("📊 检查结果:")
    print(f"Swagger UI 参数显示: {'✅ 正常' if swagger_ok else '❌ 异常'}")
    print(f"基本功能: {'✅ 正常' if function_ok else '❌ 异常'}")
    
    if swagger_ok and function_ok:
        print("\n🎉 完美！现在你可以:")
        print("  1. 在 Swagger UI 中看到所有参数")
        print("  2. 正常测试接口功能")
        print("  3. 不会再有类型错误")
        print("\n🔗 访问: http://localhost:8000/docs")
        print("\n📝 在 Request body 中你会看到:")
        print("  - prompt (文本输入框)")
        print("  - model (文本输入框)")
        print("  - image (文件选择器)")
    else:
        print("\n💩 确实还有问题，需要继续修复...")
        
    print(f"\n🏆 总体评价: {'不用吃屎了！' if swagger_ok and function_ok else '还得继续努力...'}")
