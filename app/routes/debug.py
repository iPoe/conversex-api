from fastapi import APIRouter, HTTPException
from app.schemas.schemas import DebugLogRequest
from core.config import settings
import os

router = APIRouter(prefix="/debug", tags=["debug"])

# Environment-based log paths
LOG_DIR = settings.DEBUG_LOG_DIR
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILES = {
    "A": os.path.join(LOG_DIR, "player_a_logs.txt"),
    "B": os.path.join(LOG_DIR, "player_b_logs.txt")
}

@router.post("/log")
async def log_debug(request: DebugLogRequest):
    """
    Appends a log entry to the corresponding player's log file.
    """
    player_id = "A" if request.playerName.lower() in ["let me", "core", "player a"] else "B"
    log_file = LOG_FILES.get(player_id)
    
    if not log_file:
        raise HTTPException(status_code=400, detail="Invalid player name for logging.")
        
    try:
        with open(log_file, "a") as f:
            f.write(f"[{request.timestamp}] [{request.level.upper()}] {request.message}\n")
        return {"status": "logged"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write log: {str(e)}")

@router.post("/reset")
async def reset_logs():
    """
    Clears both log files.
    """
    try:
        for log_file in LOG_FILES.values():
            if os.path.exists(log_file):
                with open(log_file, "w") as f:
                    f.truncate(0)
        return {"status": "reset"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset logs: {str(e)}")
