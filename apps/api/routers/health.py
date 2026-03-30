"""
健康检查路由
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "service": "ai-radar-api"}


@router.get("/ready")
async def readiness_check():
    """就绪检查"""
    # TODO: 检查数据库和Redis连接
    return {"status": "ready"}