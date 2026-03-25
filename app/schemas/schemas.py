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

class RollDiceRequest(BaseModel):
    playerName: str

class VoteRequest(BaseModel):
    voterName: str
    optionId: str

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
    playerName: str
    diceValue: int
    choiceEdgeId: Optional[str] = None

class MoveResponse(BaseModel):
    newPosition: BoardPosition
    remainingSteps: int
    status: str
    options: Optional[List[str]] = None
    zoneId: Optional[str] = None

class RoomResponse(BaseModel):
    roomCode: str
    gameId: UUID
    status: str
    phase: str = "rolling"
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
    phase: str = "rolling"
    currentTurnIndex: int
    totalTurns: int
    pointsToWin: int
    players: List[PlayerResponse]
    turnHistory: List[TurnRecord] = []
    currentCaseId: Optional[UUID] = None
