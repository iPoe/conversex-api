from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from app.enums import RoomStatus, GamePhase

# --- Requests ---
class RoomCreateRequest(BaseModel):
    hostName: str = Field(..., min_length=1, max_length=50)
    hostAvatar: str = Field(..., min_length=1)

class PlayerJoinRequest(BaseModel):
    playerName: str = Field(..., min_length=1, max_length=50)
    playerAvatar: str = Field(..., min_length=1)

class GameStartRequest(BaseModel):
    totalTurns: int = 10
    pointsToWin: int = 40
    isTimerEnabled: bool = False

class RollDiceRequest(BaseModel):
    playerName: str = Field(..., min_length=1)

class VoteRequest(BaseModel):
    voterName: str = Field(..., min_length=1)
    optionId: str = Field(..., min_length=1)

class ArgumentRequest(BaseModel):
    playerName: str = Field(..., min_length=1)
    argument: str = Field(..., min_length=1)

class DebugLogRequest(BaseModel):
    playerName: str
    message: str
    level: str = "info"
    timestamp: str

class BoardPosition(BaseModel):
    nodeId: str
    edgeId: Optional[str] = None
    edgeProgress: int = 0

# --- Responses ---
class RubricOption(BaseModel):
    id: str
    text: str
    points: int

class CaseResponse(BaseModel):
    caseId: UUID
    description: str
    rubric: List[RubricOption]

class PlayerResponse(BaseModel):
    name: str
    avatar: str
    isHost: bool
    onlineStatus: bool = True
    boardPosition: BoardPosition
    score: int = 0
    turnsPlayed: int = 0

class RollDiceResponse(BaseModel):
    diceValue: int

class MoveRequest(BaseModel):
    playerName: str = Field(..., min_length=1)
    diceValue: int
    choiceEdgeId: Optional[str] = None

class MoveResponse(BaseModel):
    newPosition: BoardPosition
    remainingSteps: int
    status: str
    options: Optional[List[str]] = None
    zoneId: Optional[str] = None
    caseData: Optional[CaseResponse] = None

class RoomResponse(BaseModel):
    roomCode: str
    gameId: UUID
    status: RoomStatus
    phase: GamePhase = GamePhase.ROLLING
    players: List[PlayerResponse]
    currentArgument: Optional[str] = None

class TurnRecord(BaseModel):
    turnNumber: int
    playerName: str
    diceValue: int
    caseId: str
    selectedOption: Optional[str] = None
    feedback: Dict[str, str] = {}
    pointsEarned: int
    timestamp: str

class LiveGameState(BaseModel):
    gameId: UUID
    roomCode: str
    status: RoomStatus
    phase: GamePhase = GamePhase.ROLLING
    currentTurnIndex: int
    totalTurns: int
    pointsToWin: int
    players: List[PlayerResponse]
    turnHistory: List[TurnRecord] = []
    currentCaseId: Optional[UUID] = None
    currentArgument: Optional[str] = None
