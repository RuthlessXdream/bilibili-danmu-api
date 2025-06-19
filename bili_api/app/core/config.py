import os
from pathlib import Path
from typing import Optional, List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""
    
    # API配置
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Bilibili Live API"
    
    # 日志级别
    LOG_LEVEL: str = "INFO"
    
    # CORS配置
    BACKEND_CORS_ORIGINS: List[str] = ["*"]
    
    # blivedm路径
    BLIVEDM_PATH: Path = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../blivedm/blivedm")))
    
    # B站API请求头
    BILIBILI_USER_AGENT: str = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    BILIBILI_REFERER: str = 'https://live.bilibili.com/'
    
    # 默认cookies
    DEFAULT_COOKIES: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings() 