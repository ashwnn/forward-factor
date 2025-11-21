"""FastAPI application for analytics and monitoring."""
from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services import SignalService
from typing import List, Optional

app = FastAPI(title="Forward Factor Signal Bot API", version="1.0.0")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "ff-signal-bot-api"}


@app.get("/signals")
async def get_signals(
    ticker: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """
    Get recent signals.
    
    Args:
        ticker: Optional ticker filter
        limit: Number of signals to return
    """
    signals = await SignalService.get_recent_signals(db, ticker, limit)
    
    return {
        "count": len(signals),
        "signals": [
            {
                "id": str(signal.id),
                "ticker": signal.ticker,
                "ff_value": signal.ff_value,
                "front_dte": signal.front_dte,
                "back_dte": signal.back_dte,
                "as_of_ts": signal.as_of_ts.isoformat(),
                "quality_score": signal.quality_score
            }
            for signal in signals
        ]
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
