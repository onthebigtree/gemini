# 如何在 Swagger UI 中测试 /generate 接口

## 📋 步骤说明

### 1. 打开 Swagger UI
访问：`http://localhost:8000/docs`

### 2. 找到 /generate 接口
在页面中找到 `POST /generate` 接口

### 3. 点击 "Try it out"
点击右上角的 "Try it out" 按钮

### 4. 填写参数

#### 必填参数：
- **prompt**: 输入你的文本提示词，例如："你好，请说一句话"

#### 可选参数：
- **model**: 可以留空，使用默认模型

### 5. 添加图片（可选）

如果你想要图文混合生成：

1. 在 **Request body** 区域，你会看到一个表单
2. 点击 "Add string item" 或类似按钮
3. 添加一个新字段：
   - **Key**: `image`
   - **Type**: 选择 "File" 
   - **Value**: 选择你要上传的图片文件

### 6. 执行请求
点击蓝色的 "Execute" 按钮

## 🎯 测试场景

### 纯文本生成
- 只填写 `prompt` 参数
- 不添加 `image` 字段
- 点击 Execute

### 图文混合生成  
- 填写 `prompt` 参数
- 添加 `image` 字段并上传图片
- 点击 Execute

## 📊 预期结果

### 纯文本模式
```json
{
  "success": true,
  "message": "纯文本生成成功",
  "texts": ["AI生成的文本内容"],
  "image_urls": []
}
```

### 图文混合模式
```json
{
  "success": true,
  "message": "图文混合生成成功", 
  "texts": ["AI对图片的描述"],
  "image_urls": ["生成的图片链接"]
}
```

## ⚠️ 注意事项

1. **image 参数不会自动显示**：由于 FastAPI 的限制，你需要手动添加 image 字段
2. **文件类型**：支持 JPEG, PNG, WebP, GIF 格式
3. **文件大小**：最大 10MB
4. **可选上传**：不上传图片也能正常工作（纯文本模式）

## 🔧 如果遇到问题

1. **看不到参数输入框**：刷新页面，确保点击了 "Try it out"
2. **上传失败**：检查图片格式和大小是否符合要求
3. **类型错误**：确保 image 字段类型选择为 "File" 而不是 "String"
