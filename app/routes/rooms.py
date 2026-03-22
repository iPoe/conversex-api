from fastapi import APIRouter, HTTPException
from app.schemas.schemas import (
    RoomCreateRequest, RoomResponse, PlayerJoinRequest, 
    PlayerResponse, GameStartRequest, LiveGameState, TurnRecord,
    RollDiceRequest, RollDiceResponse, VoteRequest, CaseResponse, RubricOption
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
@router.post("/rooms/{roomCode}/turn", response_model=LiveGameState)
async def record_turn(roomCode: str, turn: TurnRecord):
    # 1. Get room
    room_res = supabase.table("rooms").select("*").eq("room_code", roomCode).execute()
    if not room_res.data:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room = room_res.data[0]
    config = room.get("config", {})
    
    # 2. Update turn history in config
    turn_history = config.get("turnHistory", [])
    turn_history.append(turn.dict())
    
    # 3. Calculate new state
    # In a real app, we'd validate the turn and update player scores here
    # For now, we update the config and return the new state
    
    completed_turns = len(turn_history)
    total_turns = config.get("totalTurns", 10)
    
    new_status = "finished" if completed_turns >= total_turns else "in_progress"
    
    update_data = {
        "status": new_status,
        "config": {
            **config,
            "turnHistory": turn_history
        }
    }
    
    updated_room_res = supabase.table("rooms").update(update_data).eq("id", room["id"]).execute()
    updated_room = updated_room_res.data[0]
    
    # 4. Get players to return current standings
    players_res = supabase.table("players").select("*").eq("room_id", room["id"]).execute()
    
    # Calculate scores from turn history
    player_stats = {}
    for p in players_res.data:
        player_stats[p["name"]] = {"score": 0, "boardPosition": 0, "turnsPlayed": 0}
        
    for t in turn_history:
        p_name = t["playerName"]
        if p_name in player_stats:
            player_stats[p_name]["score"] += t["pointsEarned"]
            player_stats[p_name]["boardPosition"] += t["diceValue"]
            player_stats[p_name]["turnsPlayed"] += 1
            
    players_list = [
        PlayerResponse(
            name=p["name"],
            avatar=p["avatar_id"],
            isHost=p["is_host"],
            score=player_stats[p["name"]]["score"],
            boardPosition=player_stats[p["name"]]["boardPosition"],
            turnsPlayed=player_stats[p["name"]]["turnsPlayed"]
        ) for p in players_res.data
    ]
    
    # Next player turn
    current_turn_index = completed_turns % len(players_list) if players_list else 0
    
    return LiveGameState(
        gameId=updated_room["id"],
        roomCode=updated_room["room_code"],
        status=updated_room["status"],
        currentTurnIndex=current_turn_index,
        totalTurns=total_turns,
        pointsToWin=config.get("pointsToWin", 40),
        players=players_list,
        turnHistory=[TurnRecord(**t) for t in turn_history]
    )

@router.post("/rooms/{roomCode}/roll", response_model=RollDiceResponse)
async def roll_dice(roomCode: str, request: RollDiceRequest):
    # 1. Get room
    room_res = supabase.table("rooms").select("*").eq("room_code", roomCode).execute()
    if not room_res.data:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room = room_res.data[0]
    room_id = room["id"]
    config = room.get("config", {})
    turn_history = config.get("turnHistory", [])
    
    # 2. (Optional but recommended) Validate if it's the player's turn
    # We order by created_at to ensure consistent turn order
    players_res = supabase.table("players").select("*").eq("room_id", room_id).order("created_at").execute()
    players = players_res.data
    
    if players:
        current_turn_index = len(turn_history) % len(players)
        if players[current_turn_index]["name"] != request.playerName:
            raise HTTPException(
                status_code=403, 
                detail=f"It's not {request.playerName}'s turn. It's {players[current_turn_index]['name']}'s turn."
            )

    # 3. Generate Dice
    dice_value = random.randint(1, 6)
    
    # 4. Update Supabase Room (Broadcast via Realtime)
    # This triggers an UPDATE event that the frontend listens to
    update_data = {
        "dice_value": dice_value
    }
    supabase.table("rooms").update(update_data).eq("id", room_id).execute()
    
    return RollDiceResponse(diceValue=dice_value)

@router.get("/rooms/{roomCode}/case", response_model=CaseResponse)
async def get_current_case(roomCode: str):
    # 1. Get room and player turn
    room_res = supabase.table("rooms").select("*").eq("room_code", roomCode).execute()
    if not room_res.data:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room = room_res.data[0]
    config = room.get("config", {})
    turn_history = config.get("turnHistory", [])
    
    # 2. Find whose turn it is
    players_res = supabase.table("players").select("*").eq("room_id", room["id"]).order("created_at").execute()
    players = players_res.data
    current_player_idx = len(turn_history) % len(players)
    current_player = players[current_player_idx]
    
    # 3. Calculate board position (sum of dice values in turn history)
    board_pos = sum([t["diceValue"] for t in turn_history if t["playerName"] == current_player["name"]])
    zone = (board_pos // 10) + 1 # Simple logic: every 10 spaces is a new zone
    
    # 4. Fetch random case for that zone
    case_res = supabase.table("cases").select("*").eq("zone", zone).execute()
    if not case_res.data:
        # Fallback to any case if zone has none
        case_res = supabase.table("cases").select("*").limit(1).execute()
    
    if not case_res.data:
        raise HTTPException(status_code=404, detail="No cases found in DB")
    
    selected_case = random.choice(case_res.data)
    
    # 5. Update room phase to 'arguing'
    supabase.table("rooms").update({
        "phase": "arguing",
        "current_case_id": selected_case["id"]
    }).eq("id", room["id"]).execute()
    
    return CaseResponse(
        caseId=selected_case["id"],
        description=selected_case["description"],
        rubric=[RubricOption(**r) for r in selected_case["rubric"]]
    )

@router.post("/rooms/{roomCode}/vote")
async def cast_vote(roomCode: str, request: VoteRequest):
    room_res = supabase.table("rooms").select("*").eq("room_code", roomCode).execute()
    if not room_res.data:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room = room_res.data[0]
    
    # Insert or update vote
    vote_data = {
        "room_id": room["id"],
        "voter_name": request.voterName,
        "option_id": request.optionId
    }
    
    # Using upsert logic via Supabase (requires unique constraint on room_id + voter_name)
    supabase.table("votes").upsert(vote_data).execute()
    
    # Update phase to 'voting' if it was 'arguing'
    if room["phase"] == "arguing":
        supabase.table("rooms").update({"phase": "voting"}).eq("id", room["id"]).execute()
    
    return {"status": "vote_cast"}

@router.get("/rooms/{roomCode}/vote-results")
async def get_vote_results(roomCode: str):
    # 1. Get room and case
    room_res = supabase.table("rooms").select("*").eq("room_code", roomCode).execute()
    if not room_res.data:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room = room_res.data[0]
    case_res = supabase.table("cases").select("*").eq("id", room["current_case_id"]).execute()
    if not case_res.data:
        raise HTTPException(status_code=404, detail="Current case not found")
    
    case = case_res.data[0]
    rubric = {r["id"]: r["points"] for r in case["rubric"]}
    
    # 2. Get all votes
    votes_res = supabase.table("votes").select("*").eq("room_id", room["id"]).execute()
    votes = votes_res.data
    
    if not votes:
        return {"status": "no_votes", "pointsEarned": 0}
    
    # 3. Calculate MODE
    counts = {}
    for v in votes:
        opt = v["option_id"]
        counts[opt] = counts.get(opt, 0) + 1
    
    max_votes = max(counts.values())
    winners = [opt for opt, count in counts.items() if count == max_votes]
    
    # 4. TIE BREAKER: Option with highest points
    final_option = winners[0]
    if len(winners) > 1:
        final_option = max(winners, key=lambda opt: rubric.get(opt, 0))
    
    points_earned = rubric.get(final_option, 0)
    
    # 5. Cleanup: Delete votes for this room
    supabase.table("votes").delete().eq("room_id", room["id"]).execute()
    
    # 6. Update phase to 'rolling' for next player
    supabase.table("rooms").update({"phase": "rolling"}).eq("id", room["id"]).execute()
    
    return {
        "winnerOption": final_option,
        "pointsEarned": points_earned,
        "voteCount": counts
    }
