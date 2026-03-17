from fastapi import APIRouter, HTTPException
from app.schemas.schemas import (
    RoomCreateRequest, RoomResponse, PlayerJoinRequest, 
    PlayerResponse, GameStartRequest, LiveGameState
)
from core.database import supabase
import random
import string
from uuid import UUID

router = APIRouter()

def generate_room_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@router.post("/rooms", response_model=RoomResponse)
async def create_room(request: RoomCreateRequest):
    room_code = generate_room_code()
    
    # 1. Create room in DB
    room_data = {
        "room_code": room_code,
        "status": "waiting",
        "config": {
            "totalTurns": 10, 
            "pointsToWin": 40, 
            "isTimerEnabled": False
        }
    }
    room_res = supabase.table("rooms").insert(room_data).execute()
    if not room_res.data:
        raise HTTPException(status_code=500, detail="Error creating room")
    
    room = room_res.data[0]
    
    # 2. Add host player
    player_data = {
        "room_id": room["id"],
        "name": request.hostName,
        "avatar_id": request.hostAvatar,
        "is_host": True
    }
    player_res = supabase.table("players").insert(player_data).execute()
    if not player_res.data:
        raise HTTPException(status_code=500, detail="Error creating host")
    
    host = player_res.data[0]
    
    return RoomResponse(
        roomCode=room["room_code"],
        gameId=room["id"],
        status=room["status"],
        players=[PlayerResponse(
            name=host["name"],
            avatar=host["avatar_id"],
            isHost=host["is_host"]
        )]
    )

@router.post("/rooms/{roomCode}/join", response_model=RoomResponse)
async def join_room(roomCode: str, request: PlayerJoinRequest):
    # 1. Get room
    room_res = supabase.table("rooms").select("*").eq("room_code", roomCode).execute()
    if not room_res.data:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room = room_res.data[0]
    
    # 2. Check current players
    players_res = supabase.table("players").select("*").eq("room_id", room["id"]).execute()
    if len(players_res.data) >= 2:
        raise HTTPException(status_code=400, detail="Room is full")
    
    # 3. Add new player
    new_player_data = {
        "room_id": room["id"],
        "name": request.playerName,
        "avatar_id": request.playerAvatar,
        "is_host": False
    }
    supabase.table("players").insert(new_player_data).execute()
    
    # 4. Get updated player list
    updated_players_res = supabase.table("players").select("*").eq("room_id", room["id"]).execute()
    
    players_list = [
        PlayerResponse(
            name=p["name"],
            avatar=p["avatar_id"],
            isHost=p["is_host"]
        ) for p in updated_players_res.data
    ]
    
    return RoomResponse(
        roomCode=room["room_code"],
        gameId=room["id"],
        status=room["status"],
        players=players_list
    )

@router.post("/rooms/{roomCode}/start", response_model=LiveGameState)
async def start_game(roomCode: str, request: GameStartRequest):
    # 1. Get room
    room_res = supabase.table("rooms").select("*").eq("room_code", roomCode).execute()
    if not room_res.data:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room = room_res.data[0]
    
    # 2. Update room status and config
    update_data = {
        "status": "in_progress",
        "config": {
            "totalTurns": request.totalTurns,
            "pointsToWin": request.pointsToWin,
            "isTimerEnabled": request.isTimerEnabled
        }
    }
    updated_room_res = supabase.table("rooms").update(update_data).eq("id", room["id"]).execute()
    updated_room = updated_room_res.data[0]
    
    # 3. Get players to initialize state
    players_res = supabase.table("players").select("*").eq("room_id", room["id"]).execute()
    
    players_list = [
        PlayerResponse(
            name=p["name"],
            avatar=p["avatar_id"],
            isHost=p["is_host"],
            boardPosition=0,
            score=0,
            turnsPlayed=0
        ) for p in players_res.data
    ]
    
    return LiveGameState(
        gameId=updated_room["id"],
        roomCode=updated_room["room_code"],
        status=updated_room["status"],
        currentTurnIndex=0,
        totalTurns=updated_room["config"]["totalTurns"],
        pointsToWin=updated_room["config"]["pointsToWin"],
        players=players_list,
        turnHistory=[]
    )
