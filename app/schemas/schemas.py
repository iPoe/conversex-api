from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

# --- Requests ---
class RoomCreateRequest(BaseModel):
    hostName: str
    hostAvatar: str

class PlayerJoinRequest(BaseModel):
    playerName: str
    playerAvatar: str

class GameStartRequest(BaseModel):
    totalTurns: int = 10
    pointsToWin: int = 40
    isTimerEnabled: bool = False

# --- Responses ---
class PlayerResponse(BaseModel):
    name: str
    avatar: str
    isHost: bool
    onlineStatus: bool = True
    boardPosition: int = 0
    score: int = 0
    turnsPlayed: int = 0

class RoomResponse(BaseModel):
    roomCode: str
    gameId: UUID
    status: str
    players: List[PlayerResponse]

class TurnRecord(BaseModel):
    turnNumber: int
    playerName: str
    diceValue: int
    caseId: str
    selectedOption: Optional[int] = None
    feedback: Dict[str, str]
    pointsEarned: int
    timestamp: str

class LiveGameState(BaseModel):
    gameId: UUID
    roomCode: str
    status: str
    currentTurnIndex: int
    totalTurns: int
    pointsToWin: int
    players: List[PlayerResponse]
    turnHistory: List[TurnRecord] = []
