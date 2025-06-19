import logging
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .core.config import settings
from .api.endpoints import router as rest_router
from .api.ws import router as ws_router


# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


# 创建FastAPI应用
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="B站直播弹幕 API，提供直播间数据实时获取",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 注册路由
app.include_router(rest_router, prefix=settings.API_V1_STR)
app.include_router(ws_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    """API根路径，返回基本信息"""
    return {
        "name": settings.PROJECT_NAME,
        "version": "1.0.0",
        "description": "B站直播弹幕 API，提供直播间数据实时获取",
        "docs": "/docs",
    }


if __name__ == "__main__":
    # 启动服务器
    uvicorn.run(
        "app.main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
    ) 