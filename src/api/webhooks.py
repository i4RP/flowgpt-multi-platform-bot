"""
FastAPI webhook endpoints for LINE bot.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

_line_bot = None


def set_line_bot(bot) -> None:
    """Set the LINE bot instance for webhook handling."""
    global _line_bot
    _line_bot = bot


@router.post("/line")
async def line_webhook(
    request: Request,
    x_line_signature: Optional[str] = Header(None)
) -> dict:
    """Handle LINE webhook events."""
    if _line_bot is None:
        raise HTTPException(status_code=503, detail="LINE bot not initialized")
    
    if not x_line_signature:
        raise HTTPException(status_code=400, detail="Missing X-Line-Signature header")
    
    body = await request.body()
    body_str = body.decode("utf-8")
    
    try:
        _line_bot.handle_webhook(body_str, x_line_signature)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error handling LINE webhook: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "services": {
            "line": _line_bot is not None
        }
    }
