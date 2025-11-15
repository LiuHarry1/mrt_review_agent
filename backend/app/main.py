from __future__ import annotations

import logging
import sys
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

# 处理导入问题：先尝试相对导入，失败则使用绝对导入
_IS_MAIN = __name__ == "__main__"
# 确保 backend 目录在 sys.path 中
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

try:
    # 先尝试相对导入（作为模块导入时）
    from .config import get_config
    from .llm import LLMClient, DashScopeError
    from .models import ChatRequest, ConfigUpdateRequest, ReviewRequest, ReviewResponse
    from .logger import setup_logging
    from .service.chat import ChatService
    from .service.review import ReviewService
except ImportError:
    # 相对导入失败，使用绝对导入（直接运行时）
    from app.config import get_config
    from app.llm import LLMClient, DashScopeError
    from app.models import ChatRequest, ConfigUpdateRequest, ReviewRequest, ReviewResponse
    from app.logger import setup_logging
    from app.service.chat import ChatService
    from app.service.review import ReviewService

# Configure logging to output to both console and file
setup_logging(
    log_level=logging.INFO,
    log_dir=str(Path(__file__).parent.parent / "logs"),
    log_file="app.log",
    console_output=True,
    file_output=True
)

load_dotenv()

app = FastAPI(title="MRT Review Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# Services
llm_client = LLMClient()
review_service = ReviewService(llm_client=llm_client)
chat_service = ChatService(llm_client=llm_client)


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok"}


@app.get("/config")
def get_default_config() -> dict:
    """Get default configuration including system prompt template and checklist."""
    config = get_config()
    return {
        "system_prompt_template": config.system_prompt_template,
        "checklist": [{"id": item.id, "description": item.description} for item in config.default_checklist],
    }


@app.post("/config")
def save_config(request: ConfigUpdateRequest) -> dict:
    """Save system prompt template and checklist configuration."""
    try:
        # 动态导入以支持直接运行和模块导入
        try:
            from .config import reload_config
        except ImportError:
            from app.config import reload_config
        get_config().save_config(request.system_prompt_template, request.checklist)
        reload_config()
        return {"status": "success", "message": "Configuration saved successfully"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save configuration: {str(exc)}") from exc


@app.post("/review", response_model=ReviewResponse)
def review(request: ReviewRequest) -> ReviewResponse:
    try:
        return review_service.review(request)
    except DashScopeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/upload/file")
def upload_file(file: UploadFile = File(...)):
    """Upload and parse file, returning text content."""
    try:
        import base64
        # 动态导入以支持直接运行和模块导入
        try:
            from .service.file_parser import parse_file_content
        except ImportError:
            from app.service.file_parser import parse_file_content
        
        # Read file content
        content = file.file.read()
        file_ext = file.filename.lower().split('.')[-1] if '.' in file.filename else ''
        
        # Determine if binary or text
        if file_ext in ['pdf', 'doc', 'docx']:
            # Encode as base64
            base64_content = base64.b64encode(content).decode('utf-8')
            file_content = f"[BINARY_FILE:.{file_ext}:{base64_content}]"
        else:
            # Text file
            try:
                file_content = content.decode('utf-8')
            except UnicodeDecodeError:
                file_content = content.decode('utf-8', errors='ignore')
        
        # Parse file
        text_content = parse_file_content(file.filename, file_content)
        
        if text_content is None:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to parse file {file.filename}. Supported formats: PDF, Word (.docx), TXT, MD, JSON"
            )
        
        return {
            "filename": file.filename,
            "content": text_content,
            "size": len(text_content)
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(exc)}") from exc


@app.post("/agent/message/stream")
def agent_message_stream(request: ChatRequest):
    """Handle chat request with streaming response."""
    import json
    
    def generate():
        try:
            for chunk in chat_service.chat_stream(request):
                # Format as SSE
                data = json.dumps({"type": "chunk", "content": chunk}, ensure_ascii=False)
                yield f"data: {data}\n\n"
            # Send done signal
            yield "data: " + json.dumps({"type": "done"}, ensure_ascii=False) + "\n\n"
        except DashScopeError as exc:
            error_data = json.dumps({"type": "error", "content": str(exc)}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"
        except Exception as exc:
            error_data = json.dumps({"type": "error", "content": f"处理请求时出错：{str(exc)}"}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def main():
    """启动 FastAPI 应用"""
    # 使用导入字符串以支持 reload 功能
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main()

