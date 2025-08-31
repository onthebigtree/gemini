import os
import uuid
import time
from io import BytesIO
from typing import List, Optional
import mimetypes
import logging

from fastapi import FastAPI, File, Form, UploadFile, HTTPException, Request, Depends, Body
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
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

# ---------- Logging ----------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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

# ---------- Request Logging Middleware ----------
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    logger.info(f"📥 收到请求: {request.method} {request.url.path}")
    logger.info(f"📥 客户端: {request.client.host}:{request.client.port}")
    logger.info(f"📥 User-Agent: {request.headers.get('user-agent', 'unknown')}")
    logger.info(f"📥 Content-Type: {request.headers.get('content-type', 'unknown')}")
    
    # 如果是 /generate 接口，尝试读取更多信息
    if request.url.path == "/generate":
        try:
            # 尝试获取表单数据
            logger.info("🔍 尝试预读取表单数据...")
            body = await request.body()
            logger.info(f"🔍 请求体大小: {len(body)} bytes")
            logger.info(f"🔍 请求体前100字符: {body[:100]}")
            
            # 重新构造 request 以便后续处理
            from starlette.requests import Request as StarletteRequest
            scope = request.scope.copy()
            
            async def receive():
                return {"type": "http.request", "body": body}
            
            request = StarletteRequest(scope, receive)
        except Exception as e:
            logger.error(f"🔍 预读取表单数据失败: {e}")
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(f"📤 响应: {response.status_code} | 处理时间: {process_time:.3f}s")
        
        if response.status_code >= 400:
            logger.error(f"📤 错误响应! 状态码: {response.status_code}")
            
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"💥 中间件捕获异常: {e}")
        logger.error(f"💥 异常类型: {type(e)}")
        logger.error(f"💥 处理时间: {process_time:.3f}s")
        raise

# CORS（按需调整） - 先添加中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)

# 挂载静态文件以便访问生成的图片
app.mount("/static", StaticFiles(directory=GENERATED_DIR), name="static")

# ---------- Exception Handlers ----------
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    全局异常处理器，专门处理 /generate 接口的 image 字段验证错误
    """
    logger.error("=" * 50)
    logger.error("🚨 REQUEST VALIDATION ERROR 详细信息")
    logger.error("=" * 50)
    logger.error(f"🚨 请求验证错误! 客户端: {request.client.host}")
    logger.error(f"🚨 请求路径: {request.url.path}")
    logger.error(f"🚨 请求方法: {request.method}")
    logger.error(f"🚨 完整URL: {request.url}")
    logger.error(f"🚨 请求头: {dict(request.headers)}")
    logger.error(f"🚨 错误详情: {exc.errors()}")
    
    # 详细分析每个错误
    for i, error in enumerate(exc.errors()):
        logger.error(f"🚨 错误 #{i+1}:")
        logger.error(f"   - 类型: {error.get('type')}")
        logger.error(f"   - 位置: {error.get('loc')}")
        logger.error(f"   - 消息: {error.get('msg')}")
        logger.error(f"   - 输入值: {repr(error.get('input'))}")
        logger.error(f"   - 上下文: {error.get('ctx')}")
    
    # 尝试读取请求体信息
    try:
        logger.error("🔍 尝试读取表单数据...")
        form_data = await request.form()
        logger.error(f"🚨 表单数据字段数量: {len(form_data)}")
        logger.error(f"🚨 表单数据字段名: {list(form_data.keys())}")
        
        for key, value in form_data.items():
            if hasattr(value, 'filename'):
                logger.error(f"🚨 文件字段 {key}: filename='{value.filename}', content_type='{getattr(value, 'content_type', 'unknown')}', size={getattr(value, 'size', 'unknown')}")
            else:
                logger.error(f"🚨 文本字段 {key}: '{value}' (类型: {type(value)})")
    except Exception as e:
        logger.error(f"🚨 无法读取表单数据: {e}")
        logger.error(f"🚨 表单读取异常类型: {type(e)}")
    
    logger.error("=" * 50)
    
    # 检查是否是 /generate 接口的 image 字段错误
    # 注意：error.get("loc") 可能是元组或列表
    if (request.url.path == "/generate" and 
        any(error.get("loc") in [("body", "image"), ["body", "image"]] for error in exc.errors())):
        
        logger.info("🔄 检测到 image 字段验证错误，回退到手动处理...")
        
        try:
            # 手动解析表单数据
            form_data = await request.form()
            
            # 获取参数
            prompt = form_data.get("prompt")
            if not prompt:
                return JSONResponse(
                    status_code=200,
                    content={
                        "success": False,
                        "model": MODEL_NAME,
                        "prompt": "",
                        "texts": [],
                        "image_urls": [],
                        "message": "缺少必填参数: prompt"
                    }
                )
            
            model = form_data.get("model", None)
            model_name = model or MODEL_NAME
            
            # 处理图片参数
            image_file = None
            if "image" in form_data:
                potential_image = form_data["image"]
                if is_valid_upload_file(potential_image):
                    image_file = potential_image
                    print(f"🖼️ 异常处理器检测到有效图片: {potential_image.filename}")
                else:
                    print("📝 异常处理器：纯文本模式（image字段为空或无效）")
            else:
                print("📝 异常处理器：纯文本模式（无image字段）")
            
            # 调用处理函数
            result = await safe_generate_handler(request, prompt, model_name, image_file)
            
            # 安全地转换为字典
            if hasattr(result, 'dict'):
                content = result.dict()
            elif hasattr(result, 'model_dump'):
                content = result.model_dump()
            else:
                # 手动构建响应
                content = {
                    "success": getattr(result, 'success', True),
                    "model": getattr(result, 'model', model_name),
                    "prompt": getattr(result, 'prompt', prompt),
                    "texts": getattr(result, 'texts', []),
                    "image_urls": getattr(result, 'image_urls', []),
                    "message": getattr(result, 'message', "生成成功")
                }
            
            # 转换为 JSONResponse
            return JSONResponse(
                status_code=200,
                content=content
            )
            
        except Exception as e:
            print(f"🚨 异常处理器内部错误: {e}")
            return JSONResponse(
                status_code=200,
                content={
                    "success": False,
                    "model": MODEL_NAME,
                    "prompt": "",
                    "texts": [],
                    "image_urls": [],
                    "message": f"异常处理器处理失败: {str(e)}"
                }
            )
    
    # 对于其他验证错误，返回标准错误响应
    print(f"🚨 非 /generate 接口错误或非 image 字段错误，返回标准错误")
    # 安全地处理错误信息，避免 JSON 序列化问题
    try:
        error_details = []
        for error in exc.errors():
            safe_error = {
                "type": error.get("type", "unknown"),
                "loc": error.get("loc", []),
                "msg": str(error.get("msg", "Validation error")),
                "input": str(error.get("input", ""))
            }
            error_details.append(safe_error)
        
        return JSONResponse(
            status_code=422,
            content={"detail": error_details}
        )
    except Exception:
        # 如果还是有问题，返回简化的错误信息
        return JSONResponse(
            status_code=422,
            content={"detail": [{"type": "validation_error", "msg": "Request validation failed"}]}
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

async def _process_generate_request(
    request: Request,
    prompt: str,
    model_name: str,
    image_file = None
) -> GenerateResponse:
    """处理生成请求的内部函数"""
    try:
        # 初始化客户端
        client = get_client()

        # 准备内容
        contents = [prompt]
        
        # 如果有图片，添加到内容中
        if image_file and hasattr(image_file, 'filename') and image_file.filename and image_file.filename.strip():
            try:
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

    except Exception as e:
        return GenerateResponse(
            success=False,
            model=model_name,
            prompt=prompt,
            texts=[],
            image_urls=[],
            message=f"请求处理失败: {str(e)}"
        )

def is_valid_upload_file(image) -> bool:
    """检查是否是有效的文件上传"""
    if image is None:
        return False
    
    # 检查是否是字符串（FastAPI bug 情况）
    if isinstance(image, str):
        return False
    
    # 检查是否有 filename 属性
    if not hasattr(image, 'filename'):
        return False
    
    # 检查文件名是否有效
    if not image.filename or not image.filename.strip() or image.filename == "":
        return False
    
    return True

async def safe_generate_handler(
    request: Request,
    prompt: str,
    model: Optional[str] = None,
    image: Optional[UploadFile] = None,
):
    """安全的生成处理函数，处理可选文件上传的各种情况"""
    try:
        model_name = model or MODEL_NAME
        
        # 智能处理图片参数
        image_file = None
        
        # 只有在确实有有效文件上传时才使用图片
        if is_valid_upload_file(image):
            image_file = image
            print(f"🖼️ 检测到有效图片上传: {image.filename}")
        else:
            print("📝 纯文本模式（无有效图片上传）")
        
        return await _process_generate_request(request, prompt, model_name, image_file)
        
    except Exception as e:
        return GenerateResponse(
            success=False,
            model=model or MODEL_NAME,
            prompt=prompt,
            texts=[],
            image_urls=[],
            message=f"请求处理失败: {str(e)}"
        )

@app.post("/generate")
async def generate(request: Request):
    """
    智能生成接口
    支持纯文本生成和图文混合生成两种模式：
    - 不上传图片：纯文本生成  
    - 上传图片：图文混合生成
    
    参数（通过 multipart/form-data）：
    - prompt: 文本提示词 (必填)
    - image: 图片文件 (可选)
    - model: 自定义模型名 (可选)
    """
    logger.info(f"✅ /generate 接口被调用! 客户端: {request.client.host}")
    
    try:
        # 检查 Content-Type
        content_type = request.headers.get("content-type", "")
        logger.info(f"🔍 Content-Type: {content_type}")
        
        # 如果是 multipart/form-data 但缺少 boundary，尝试手动解析
        if content_type.startswith("multipart/form-data") and "boundary=" not in content_type:
            logger.warning("⚠️ multipart/form-data 缺少 boundary 参数，尝试手动解析...")
            
            # 读取原始请求体
            body = await request.body()
            body_str = body.decode('utf-8', errors='ignore')
            
            logger.info(f"🔍 原始请求体: {body_str[:500]}...")
            
            # 尝试提取 boundary
            if body_str.startswith('--'):
                first_line = body_str.split('\r\n')[0]
                boundary = first_line[2:]  # 去掉前面的 --
                logger.info(f"🔍 提取到的 boundary: {boundary}")
                
                # 重新设置正确的 Content-Type
                import re
                
                # 解析字段
                fields = {}
                
                # 分割各个字段
                parts = body_str.split(f'--{boundary}')
                for part in parts:
                    if 'Content-Disposition: form-data' in part:
                        # 提取字段名
                        name_match = re.search(r'name="([^"]+)"', part)
                        if name_match:
                            field_name = name_match.group(1)
                            
                            # 找到头部和内容的分界线（空行）
                            if '\r\n\r\n' in part:
                                # 分割头部和内容
                                header_part, content_part = part.split('\r\n\r\n', 1)
                                # 获取纯内容（去掉可能的尾部boundary）
                                field_value = content_part.split('\r\n--')[0].strip()
                            else:
                                # 备用解析方法
                                lines = part.split('\r\n')
                                content_lines = []
                                found_empty_line = False
                                
                                for line in lines:
                                    if found_empty_line:
                                        if line.startswith('--'):
                                            break
                                        content_lines.append(line)
                                    elif line == "":
                                        found_empty_line = True
                                
                                field_value = '\r\n'.join(content_lines).strip()
                            
                            fields[field_name] = field_value
                            logger.info(f"🔍 解析字段: {field_name} = '{field_value}'")
                
                # 使用解析的字段
                prompt = fields.get("prompt")
                model = fields.get("model", None)
                
                logger.info(f"✅ 手动解析到参数 - prompt: '{prompt}', model: '{model}'")
                
                if not prompt:
                    logger.error("❌ 缺少必填参数: prompt")
                    return JSONResponse(
                        status_code=200,
                        content={
                            "success": False,
                            "model": MODEL_NAME,
                            "prompt": "",
                            "texts": [],
                            "image_urls": [],
                            "message": "缺少必填参数: prompt"
                        }
                    )
                
                model_name = model or MODEL_NAME
                
                # 处理图片参数（手动解析的情况下，如果 image 字段为空字符串，就是纯文本）
                image_file = None
                image_value = fields.get("image", "")
                if image_value and image_value.strip():
                    logger.info(f"🖼️ 检测到图片字段（但手动解析无法处理文件）: {image_value}")
                    # 手动解析模式下，暂时不支持图片上传
                    logger.info("📝 手动解析模式：纯文本模式")
                else:
                    logger.info("📝 手动解析模式：纯文本模式（无image字段或为空）")
                
                # 调用处理函数
                result = await safe_generate_handler(request, prompt, model_name, None)  # 手动解析模式暂不支持图片
                
                # 返回结果
                if hasattr(result, 'dict'):
                    content = result.dict()
                elif hasattr(result, 'model_dump'):
                    content = result.model_dump()
                else:
                    content = {
                        "success": getattr(result, 'success', True),
                        "model": getattr(result, 'model', model_name),
                        "prompt": getattr(result, 'prompt', prompt),
                        "texts": getattr(result, 'texts', []),
                        "image_urls": getattr(result, 'image_urls', []),
                        "message": getattr(result, 'message', "生成成功")
                    }
                
                return JSONResponse(status_code=200, content=content)
            
            else:
                logger.error("❌ 无法解析 multipart 数据：找不到 boundary")
                return JSONResponse(
                    status_code=200,
                    content={
                        "success": False,
                        "model": MODEL_NAME,
                        "prompt": "",
                        "texts": [],
                        "image_urls": [],
                        "message": "无法解析请求：multipart/form-data 格式错误"
                    }
                )
        
        # 正常的 multipart/form-data 处理
        logger.info("🔍 开始正常解析表单数据...")
        form_data = await request.form()
        
        logger.info(f"🔍 表单字段数量: {len(form_data)}")
        logger.info(f"🔍 表单字段名: {list(form_data.keys())}")
        
        # 获取参数
        prompt = form_data.get("prompt")
        model = form_data.get("model", None)
        
        logger.info(f"✅ 解析到参数 - prompt: '{prompt}', model: '{model}'")
        
        if not prompt:
            logger.error("❌ 缺少必填参数: prompt")
            return JSONResponse(
                status_code=200,
                content={
                    "success": False,
                    "model": MODEL_NAME,
                    "prompt": "",
                    "texts": [],
                    "image_urls": [],
                    "message": "缺少必填参数: prompt"
                }
            )
        
        model_name = model or MODEL_NAME
        
        # 处理图片参数
        image_file = None
        if "image" in form_data:
            potential_image = form_data["image"]
            logger.info(f"🔍 检查 image 字段: 类型={type(potential_image)}, 值={repr(potential_image)}")
            
            if is_valid_upload_file(potential_image):
                image_file = potential_image
                logger.info(f"🖼️ 检测到有效图片上传: {potential_image.filename}")
            else:
                logger.info("📝 纯文本模式（image字段为空或无效）")
        else:
            logger.info("📝 纯文本模式（无image字段）")
        
        # 调用处理函数
        result = await safe_generate_handler(request, prompt, model_name, image_file)
        
        # 返回结果
        if hasattr(result, 'dict'):
            content = result.dict()
        elif hasattr(result, 'model_dump'):
            content = result.model_dump()
        else:
            # 手动构建响应
            content = {
                "success": getattr(result, 'success', True),
                "model": getattr(result, 'model', model_name),
                "prompt": getattr(result, 'prompt', prompt),
                "texts": getattr(result, 'texts', []),
                "image_urls": getattr(result, 'image_urls', []),
                "message": getattr(result, 'message', "生成成功")
            }
        
        return JSONResponse(status_code=200, content=content)
            
    except Exception as e:
        logger.error(f"💥 /generate 接口处理失败: {e}")
        logger.error(f"💥 异常类型: {type(e)}")
        import traceback
        logger.error(f"💥 完整异常信息: {traceback.format_exc()}")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": False,
                "model": MODEL_NAME,
                "prompt": "",
                "texts": [],
                "image_urls": [],
                "message": f"请求处理失败: {str(e)}"
            }
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
                "content_type": "multipart/form-data",
                "parameters": {
                    "prompt": "文本提示词 (必填，form字段)",
                    "image": "可选，参考图片文件 (form字段，文件类型)",
                    "model": "可选，自定义模型名 (form字段)"
                },
                "response": {
                    "success": "boolean",
                    "model": "string", 
                    "prompt": "string",
                    "texts": "array of strings",
                    "image_urls": "array of strings (完整访问链接)",
                    "message": "string (包含生成模式信息)"
                },
                "usage": {
                    "text_only": "curl -F 'prompt=你的文本' http://localhost:8000/generate",
                    "with_image": "curl -F 'prompt=描述图片' -F 'image=@image.jpg' http://localhost:8000/generate"
                },
                "logic": {
                    "no_image": "不传image字段或传空文件 → 纯文本生成",
                    "with_image": "传有效图片文件 → 图文混合生成"
                },
                "swagger_usage": {
                    "step1": "在 Swagger UI 中点击 'Try it out'",
                    "step2": "填写 prompt 参数（必填）",
                    "step3": "可选填写 model 参数", 
                    "step4": "可选上传 image 文件（直接在 image 字段选择文件）",
                    "step5": "点击 Execute 执行"
                },
                "note": "现在所有参数都在 Swagger UI 中可见，包括 image 文件上传"
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

