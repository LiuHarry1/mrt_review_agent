from __future__ import annotations

import logging
import sys
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure backend directory is in sys.path for imports
_backend_dir = Path(__file__).parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

# Use absolute imports for consistency
from app.api import (
    chat_router,
    common_router,
    review_router,
    setup_chat_routes,
    setup_review_routes,
)
from app.logger import setup_logging
from app.llm import LLMClient
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

# Initialize services
llm_client = LLMClient()
review_service = ReviewService(llm_client=llm_client)
chat_service = ChatService(llm_client=llm_client)

# Setup routes with service dependencies
setup_chat_routes(chat_service=chat_service)
setup_review_routes(review_service=review_service)

# Register routers
app.include_router(common_router)
app.include_router(review_router)
app.include_router(chat_router)


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

