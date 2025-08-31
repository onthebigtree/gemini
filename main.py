import os
import uuid
from io import BytesIO
from typing import List, Optional
import mimetypes

from fastapi import FastAPI, File, Form, UploadFile, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from PIL import Image
from pydantic import BaseModel
from dotenv import load_dotenv

# google-genai: pip install google-genai
from google import genai

# 加载 .env 文件
load_dotenv()

# ---------- Config ----------
API_KEY = os.getenv("GOOGLE_API_KEY")  # 在环境变量里设置
MODEL_NAME = "gemini-2.5-flash-image-preview"
GENERATED_DIR = os.getenv("GENERATED_DIR", "static")
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

os.makedirs(GENERATED_DIR, exist_ok=True)

# ---------- Models ----------
class UploadResponse(BaseModel):
    success: bool
    message: str
    image_url: Optional[str] = None
    filename: Optional[str] = None

class GenerateResponse(BaseModel):
    success: bool
    model: str
    prompt: str
    texts: List[str]
    image_urls: List[str]
    message: Optional[str] = None

# ---------- App ----------
app = FastAPI(title="Gemini Image Gen FastAPI", version="1.0.0")

# 挂载静态文件以便访问生成的图片
app.mount("/static", StaticFiles(directory=GENERATED_DIR), name="static")

# CORS（按需调整）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)

# ---------- Client ----------
if not API_KEY:
    # 允许应用启动，但在请求阶段抛错，方便容器化/平台注入环境变量
    pass

def get_client() -> genai.Client:
    if not API_KEY:
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY not set in environment.")
    return genai.Client(api_key=API_KEY)

# ---------- Utils ----------
def validate_image_file(upload: UploadFile) -> None:
    """验证上传的图片文件"""
    # 如果没有文件名或文件名为空，跳过验证
    if not upload or not hasattr(upload, 'filename') or not upload.filename or not upload.filename.strip():
        return
        
    # 检查文件大小
    if hasattr(upload, 'size') and upload.size and upload.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413, 
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB"
        )
    
    # 检查文件类型
    content_type = upload.content_type
    if content_type and content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_IMAGE_TYPES)}"
        )

def pil_from_upload(upload: UploadFile) -> Image.Image:
    """从上传文件创建PIL图像对象"""
    try:
        # 检查是否有有效的文件
        if not upload or not hasattr(upload, 'filename') or not upload.filename or not upload.filename.strip():
            raise HTTPException(status_code=400, detail="No valid image file provided")
            
        # 验证文件
        validate_image_file(upload)
        
        # 读取文件内容
        content = upload.file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Empty file provided")
            
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB"
            )
        
        img = Image.open(BytesIO(content))
        # 确保已加载像素（避免懒加载文件句柄被关闭）
        img.load()
        return img
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image file: {e}") from e

def save_pil(img: Image.Image, suffix: str = ".png") -> str:
    """保存PIL图像并返回文件名"""
    filename = f"{uuid.uuid4().hex}{suffix}"
    path = os.path.join(GENERATED_DIR, filename)
    # 如果是带透明背景的 PNG，保持模式；否则统一转成 RGB 以避免某些格式问题
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    img.save(path)
    return filename

def save_uploaded_image(upload: UploadFile) -> tuple[str, str]:
    """保存上传的图片并返回文件名和URL"""
    # 获取原始文件扩展名
    original_filename = upload.filename or "image"
    _, ext = os.path.splitext(original_filename)
    if not ext:
        ext = ".png"  # 默认扩展名
    
    # 转换为PIL图像并保存
    pil_img = pil_from_upload(upload)
    filename = save_pil(pil_img, suffix=ext)
    image_url = f"/static/{filename}"
    
    return filename, image_url

# ---------- Routes ----------
@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/upload", response_model=UploadResponse)
async def upload_image(
    request: Request,
    image: UploadFile = File(..., description="上传的图片文件")
):
    """
    上传图片接口
    支持的格式：JPEG, PNG, WebP, GIF
    最大文件大小：10MB
    返回图片访问链接
    """
    try:
        filename, image_url = save_uploaded_image(image)
        
        # 构建完整的URL（包含域名）
        base_url = str(request.base_url).rstrip('/')
        full_image_url = f"{base_url}{image_url}"
        
        return UploadResponse(
            success=True,
            message="图片上传成功",
            image_url=full_image_url,
            filename=filename
        )
    except HTTPException as e:
        return UploadResponse(
            success=False,
            message=e.detail
        )
    except Exception as e:
        return UploadResponse(
            success=False,
            message=f"上传失败: {str(e)}"
        )

@app.post("/generate", response_model=GenerateResponse)
async def generate(
    request: Request,
    prompt: str = Form(..., description="文本提示词"),
    model: Optional[str] = Form(None, description="可选，自定义模型名，默认使用 gemini-2.5-flash-image-preview"),
):
    """
    智能生成接口
    支持纯文本生成和图文混合生成两种模式：
    - 不上传图片：纯文本生成
    - 上传图片：图文混合生成
    """
    try:
        # 选择模型
        model_name = model or MODEL_NAME

        # 初始化客户端
        client = get_client()

        # 准备内容 - 从 request.form() 中获取所有数据
        form_data = await request.form()
        contents = [prompt]
        
        # 检查是否有图片上传
        if "image" in form_data:
            image_file = form_data["image"]
            # 检查是否是有效的文件上传
            if hasattr(image_file, 'filename') and image_file.filename and image_file.filename.strip():
                try:
                    # 创建临时的 UploadFile 对象来复用现有的处理逻辑
                    pil_img = pil_from_upload(image_file)
                    contents.append(pil_img)
                except Exception as e:
                    return GenerateResponse(
                        success=False,
                        model=model_name,
                        prompt=prompt,
                        texts=[],
                        image_urls=[],
                        message=f"图片处理失败: {str(e)}"
                    )

        # 调用生成
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
            )
        except Exception as e:
            return GenerateResponse(
                success=False,
                model=model_name,
                prompt=prompt,
                texts=[],
                image_urls=[],
                message=f"AI生成失败: {str(e)}"
            )

        # 解析结果
        texts: List[str] = []
        image_urls: List[str] = []
        base_url = str(request.base_url).rstrip('/')

        try:
            candidate = response.candidates[0]
            parts = getattr(candidate.content, "parts", []) or []

            for part in parts:
                # 文本
                if getattr(part, "text", None) is not None:
                    texts.append(part.text)
                # 图片（inline_data）
                elif getattr(part, "inline_data", None) is not None:
                    data = part.inline_data.data  # bytes
                    # 用 PIL 打开并保存
                    gen_img = Image.open(BytesIO(data))
                    gen_img.load()
                    # 根据格式决定后缀
                    fmt = (gen_img.format or "PNG").lower()
                    suffix = ".png" if fmt not in (".jpg", ".jpeg", ".png", ".webp") else fmt
                    if not suffix.startswith("."):
                        suffix = f".{suffix}"

                    filename = save_pil(gen_img, suffix=suffix)
                    # 构建完整URL
                    full_image_url = f"{base_url}/static/{filename}"
                    image_urls.append(full_image_url)

        except Exception as e:
            return GenerateResponse(
                success=False,
                model=model_name,
                prompt=prompt,
                texts=[],
                image_urls=[],
                message=f"解析AI输出失败: {str(e)}"
            )

        # 确定生成模式
        mode = "图文混合生成" if len(contents) > 1 else "纯文本生成"
        
        return GenerateResponse(
            success=True,
            model=model_name,
            prompt=prompt,
            texts=texts,
            image_urls=image_urls,
            message=f"{mode}成功"
        )

    except HTTPException as e:
        return GenerateResponse(
            success=False,
            model=model or MODEL_NAME,
            prompt=prompt,
            texts=[],
            image_urls=[],
            message=e.detail
        )
    except Exception as e:
        return GenerateResponse(
            success=False,
            model=model or MODEL_NAME,
            prompt=prompt,
            texts=[],
            image_urls=[],
            message=f"请求处理失败: {str(e)}"
        )

# 便捷的根路由
@app.get("/")
def index():
    return {
        "service": "Gemini Image Generation API",
        "version": "1.0.0",
        "endpoints": {
            "upload": {
                "method": "POST",
                "path": "/upload",
                "description": "上传图片并获取访问链接",
                "parameters": {
                    "image": "图片文件 (支持 JPEG, PNG, WebP, GIF, 最大10MB)"
                },
                "response": {
                    "success": "boolean",
                    "message": "string",
                    "image_url": "string (完整访问链接)",
                    "filename": "string"
                }
            },
            "generate": {
                "method": "POST",
                "path": "/generate",
                "description": "智能生成接口，自动识别模式",
                "parameters": {
                    "prompt": "文本提示词 (必填)",
                    "image": "可选，参考图片文件",
                    "model": "可选，自定义模型名"
                },
                "response": {
                    "success": "boolean",
                    "model": "string", 
                    "prompt": "string",
                    "texts": "array of strings",
                    "image_urls": "array of strings (完整访问链接)",
                    "message": "string (包含生成模式信息)"
                },
                "modes": {
                    "text_only": "只传 prompt → 纯文本生成",
                    "image_text": "传 prompt + image → 图文混合生成"
                }
            },
            "health": {
                "method": "GET",
                "path": "/health", 
                "description": "健康检查"
            }
        },
        "docs": "/docs",
        "openapi": "/openapi.json"
    }

