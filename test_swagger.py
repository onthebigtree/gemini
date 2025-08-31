#!/usr/bin/env python3
"""
测试 Swagger UI 中是否正确显示所有参数
"""

import requests
import json

def test_openapi_schema():
    """检查 OpenAPI schema 中是否包含 image 参数"""
    print("🔍 检查 OpenAPI schema...")
    
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
        content = request_body.get("content", {})
        form_data = content.get("multipart/form-data", {})
        properties = form_data.get("schema", {}).get("properties", {})
        
        print(f"📋 /generate 端点的参数:")
        for param_name, param_info in properties.items():
            param_type = param_info.get("type", "unknown")
            param_format = param_info.get("format", "")
            required = param_name in form_data.get("schema", {}).get("required", [])
            
            print(f"  - {param_name}: {param_type} {param_format} {'(必填)' if required else '(可选)'}")
        
        # 检查是否包含所有期望的参数
        expected_params = ["prompt", "model", "image"]
        missing_params = []
        
        for param in expected_params:
            if param not in properties:
                missing_params.append(param)
        
        if missing_params:
            print(f"❌ 缺少参数: {missing_params}")
            return False
        else:
            print("✅ 所有参数都在 schema 中！")
            return True
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

def test_text_only_request():
    """测试纯文本请求"""
    print("\n🧪 测试纯文本请求...")
    
    data = {"prompt": "说一句话"}
    
    try:
        response = requests.post("http://localhost:8000/generate", data=data)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 成功! 模式: {result.get('message', '')}")
            return True
        else:
            print(f"❌ 失败: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 请求错误: {e}")
        return False

if __name__ == "__main__":
    print("🚀 测试 Swagger UI 参数显示和功能...")
    
    schema_ok = test_openapi_schema()
    request_ok = test_text_only_request()
    
    print(f"\n📊 测试结果:")
    print(f"Schema 检查: {'✅ 通过' if schema_ok else '❌ 失败'}")
    print(f"功能测试: {'✅ 通过' if request_ok else '❌ 失败'}")
    
    if schema_ok and request_ok:
        print("\n🎉 所有测试通过！Swagger UI 应该正确显示所有参数！")
    else:
        print("\n⚠️ 部分测试失败")
