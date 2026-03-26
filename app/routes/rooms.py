from fastapi import APIRouter, HTTPException
from app.schemas.schemas import (
    RoomCreateRequest, RoomResponse, PlayerJoinRequest, 
    PlayerResponse, GameStartRequest, LiveGameState, TurnRecord,
    RollDiceRequest, RollDiceResponse, VoteRequest, CaseResponse, 
    RubricOption, BoardPosition, MoveRequest, MoveResponse, ArgumentRequest
)
from core.database import supabase
from core.board import move_player, BOARD_NODES, get_outgoing_edges
import random
import string
from uuid import UUID
from datetime import datetime

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
        "phase": "rolling",
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
        "is_host": True,
        "current_position": {"nodeId": "park", "edgeId": None, "edgeProgress": 0}
    }
    player_res = supabase.table("players").insert(player_data).execute()
    if not player_res.data:
        raise HTTPException(status_code=500, detail="Error creating host")
    
    host = player_res.data[0]
    
    return RoomResponse(
        roomCode=room["room_code"],
        gameId=room["id"],
        status=room["status"],
        phase=room["phase"],
        players=[PlayerResponse(
            name=host["name"],
            avatar=host["avatar_id"],
            isHost=host["is_host"],
            boardPosition=BoardPosition(**host["current_position"])
        )],
        currentArgument=room.get("current_argument")
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
        "is_host": False,
        "current_position": {"nodeId": "park", "edgeId": None, "edgeProgress": 0}
    }
    supabase.table("players").insert(new_player_data).execute()
    
    # 4. Get updated player list
    updated_players_res = supabase.table("players").select("*").eq("room_id", room["id"]).execute()
    
    players_list = [
        PlayerResponse(
            name=p["name"],
            avatar=p["avatar_id"],
            isHost=p["is_host"],
            boardPosition=BoardPosition(**p["current_position"])
        ) for p in updated_players_res.data
    ]
    
    return RoomResponse(
        roomCode=room["room_code"],
        gameId=room["id"],
        status=room["status"],
        phase=room["phase"],
        players=players_list,
        currentArgument=room.get("current_argument")
    )

@router.get("/rooms/{roomCode}", response_model=LiveGameState)
async def get_room_state(roomCode: str):
    # 1. Get room
    room_res = supabase.table("rooms").select("*").eq("room_code", roomCode).execute()
    if not room_res.data:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room = room_res.data[0]
    room_id = room["id"]
    config = room.get("config", {})
    turn_history = config.get("turnHistory", [])
    
    # 2. Get players
    players_res = supabase.table("players").select("*").eq("room_id", room_id).order("created_at").execute()
    
    players_list = [
        PlayerResponse(
            name=p["name"],
            avatar=p["avatar_id"],
            isHost=p["is_host"],
            boardPosition=BoardPosition(**p["current_position"]),
            score=p.get("score", 0),
            turnsPlayed=p.get("turns_played", 0)
        ) for p in players_res.data
    ]
    
    # 3. Calculate current turn index
    current_turn_index = len(turn_history) % len(players_list) if players_list else 0
    
    return LiveGameState(
        gameId=room_id,
        roomCode=room["room_code"],
        status=room["status"],
        phase=room["phase"],
        currentTurnIndex=current_turn_index,
        totalTurns=config.get("totalTurns", 10),
        pointsToWin=config.get("pointsToWin", 40),
        players=players_list,
        turnHistory=[TurnRecord(**t) for t in turn_history],
        currentCaseId=room.get("current_case_id"),
        currentArgument=room.get("current_argument")
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
        "phase": "rolling",
        "config": {
            "totalTurns": request.totalTurns,
            "pointsToWin": request.pointsToWin,
            "isTimerEnabled": request.isTimerEnabled,
            "turnHistory": [],
            "current_turn_index": 0,
            "completed_turns": 0
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
            boardPosition=BoardPosition(**p["current_position"]),
            score=0,
            turnsPlayed=0
        ) for p in players_res.data
    ]
    
    return LiveGameState(
        gameId=updated_room["id"],
        roomCode=updated_room["room_code"],
        status=updated_room["status"],
        phase=updated_room["phase"],
        currentTurnIndex=0,
        totalTurns=updated_room["config"]["totalTurns"],
        pointsToWin=updated_room["config"]["pointsToWin"],
        players=players_list,
        turnHistory=[],
        currentArgument=None
    )

@router.post("/rooms/{roomCode}/argue")
async def submit_argument(roomCode: str, request: ArgumentRequest):
    # 1. Get room
    room_res = supabase.table("rooms").select("*").eq("room_code", roomCode).execute()
    if not room_res.data:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room = room_res.data[0]
    
    # 2. Update room with argument and change phase to 'voting'
    # This acts as the broadcast for observers
    supabase.table("rooms").update({
        "current_argument": request.argument,
        "phase": "voting"
    }).eq("id", room["id"]).execute()
    
    return {"status": "argument_submitted"}

@router.post("/rooms/{roomCode}/move", response_model=MoveResponse)
async def move_player_route(roomCode: str, request: MoveRequest):
    # 1. Get room and player
    room_res = supabase.table("rooms").select("*").eq("room_code", roomCode).execute()
    if not room_res.data:
        raise HTTPException(status_code=404, detail="Room not found")
    room = room_res.data[0]
    
    player_res = supabase.table("players").select("*").eq("room_id", room["id"]).eq("name", request.playerName).execute()
    if not player_res.data:
        raise HTTPException(status_code=404, detail="Player not found")
    player = player_res.data[0]
    
    # NEW: Turn Validation
    # Ensure it's actually this player's turn before allowing movement
    players_res = supabase.table("players").select("*").eq("room_id", room["id"]).order("created_at").execute()
    all_players = players_res.data
    config = room.get("config", {})
    turn_history = config.get("turnHistory", [])
    
    if all_players:
        current_turn_index = len(turn_history) % len(all_players)
        if all_players[current_turn_index]["name"] != request.playerName:
            raise HTTPException(
                status_code=403,
                detail=f"It's not {request.playerName}'s turn."
            )

    # 2. Execute movement logic
    current_pos = BoardPosition(**player["current_position"])
    move_result = move_player(current_pos, request.diceValue, request.choiceEdgeId)
    
    # 3. Prepare Atomic Update Data
    new_pos = move_result["newPosition"]
    
    # Metadata for frontend tracking
    new_config = config.copy()
    new_config["last_action_by"] = request.playerName
    new_config["branch_choice"] = request.choiceEdgeId
    
    # Phase and dice logic
    new_phase = "rolling"
    new_zone_id = None
    new_dice_value = room.get("dice_value") # Keep by default
    new_status = room.get("status", "in_progress")
    
    case_response = None
    if move_result["status"] == "waiting_choice":
        new_phase = "moving"
    elif move_result["status"] == "zone_reached":
        new_phase = "arguing"
        new_zone_id = move_result["zoneId"]
        new_dice_value = None
        
        # --- Native Case Fetching ---
        ZONE_MAP = {
            "hospital": 1, "wifi": 2, "home": 3, 
            "neighborhood": 4, "school": 5
        }
        zone_number = ZONE_MAP.get(new_zone_id, 1)
        
        case_res = supabase.table("cases").select("*").eq("zone", zone_number).execute()
        if not case_res.data:
            case_res = supabase.table("cases").select("*").limit(1).execute()
        
        if case_res.data:
            selected_case = random.choice(case_res.data)
            new_config["current_case_id"] = selected_case["id"]
            new_config["current_case_data"] = selected_case
            
            case_response = CaseResponse(
                caseId=selected_case["id"],
                description=selected_case["description"],
                rubric=[RubricOption(**r) for r in selected_case["rubric"]]
            )
    else:
        # Movement finished on a normal tile -> Advance Turn
        new_phase = "rolling"
        new_dice_value = None
        
        new_turn = {
            "turnNumber": len(turn_history) + 1,
            "playerName": request.playerName,
            "diceValue": request.diceValue,
            "caseId": "none",
            "selectedOption": None,
            "feedback": {},
            "pointsEarned": 0,
            "timestamp": datetime.now().isoformat()
        }
        new_config["turnHistory"] = turn_history + [new_turn]
        
        # Calculate new turn indices and wrap around
        total_players = len(all_players) if all_players else 1
        current_index = config.get("current_turn_index", len(turn_history) % total_players)
        curr_completed = config.get("completed_turns", len(turn_history) // total_players)
        
        new_index = (current_index + 1) % total_players
        new_config["current_turn_index"] = new_index
        
        if new_index == 0:
            new_config["completed_turns"] = curr_completed + 1
        else:
            new_config["completed_turns"] = curr_completed
        
        if len(new_config["turnHistory"]) >= config.get("totalTurns", 10):
            new_status = "finished"
            new_phase = "finished"

    # 4. EXECUTE ATOMIC TRANSACTION VIA RPC
    # This replaces the two separate .update() calls
    try:
        supabase.rpc("commit_player_move", {
            "p_room_id": str(room["id"]),
            "p_player_id": str(player["id"]),
            "p_new_position": new_pos.dict(),
            "p_new_phase": new_phase,
            "p_new_dice_value": new_dice_value,
            "p_new_zone_id": new_zone_id,
            "p_new_config": new_config,
            "p_new_status": new_status
        }).execute()
        
        # FIX: The SQL RPC uses COALESCE(p_new_dice_value, dice_value) which prevents NULL 
        # from overwriting existing dice values on turn end. Forcefully clear it if necessary.
        update_cols = {}
        if new_dice_value is None:
            update_cols["dice_value"] = None
        
        # Keep root column in sync with config
        if new_config.get("current_case_id"):
            update_cols["current_case_id"] = new_config["current_case_id"]
        
        if update_cols:
            supabase.table("rooms").update(update_cols).eq("id", room["id"]).execute()
            
    except Exception as e:
        # Fallback if RPC is not yet implemented in DB, or handle error
        raise HTTPException(status_code=500, detail=f"Atomic update failed: {str(e)}")
    
    return MoveResponse(
        newPosition=new_pos,
        remainingSteps=move_result["remainingSteps"],
        status=move_result["status"],
        options=move_result.get("options"),
        zoneId=move_result.get("zoneId"),
        caseData=case_response
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
    player_positions = updated_room["config"].get("playerPositions", {})
    
    # Calculate scores from turn history
    player_stats = {}
    for p in players_res.data:
        player_stats[p["name"]] = {"score": 0, "boardPosition": player_positions.get(p["name"], {"nodeId": "park", "edgeId": None, "edgeProgress": 0}), "turnsPlayed": 0}
        
    for t in turn_history:
        p_name = t["playerName"]
        if p_name in player_stats:
            player_stats[p_name]["score"] += t["pointsEarned"]
            player_stats[p_name]["turnsPlayed"] += 1
            
    players_list = [
        PlayerResponse(
            name=p["name"],
            avatar=p["avatar_id"],
            isHost=p["is_host"],
            score=player_stats[p["name"]]["score"],
            boardPosition=BoardPosition(**player_stats[p["name"]]["boardPosition"]),
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
    dice_value = random.randint(11, 12)
    
    # 4. Update Supabase Room (Broadcast via Realtime)
    # This triggers an UPDATE event that the frontend listens to
    update_data = {
        "dice_value": dice_value
    }
    supabase.table("rooms").update(update_data).eq("id", room_id).execute()
    
    return RollDiceResponse(diceValue=dice_value)


@router.post("/rooms/{roomCode}/vote")
async def cast_vote(roomCode: str, request: VoteRequest):
    # 1. Get room
    room_res = supabase.table("rooms").select("*").eq("room_code", roomCode).execute()
    if not room_res.data:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room = room_res.data[0]
    room_id = room["id"]
    
    # 2. Insert or update vote
    vote_data = {
        "room_id": room_id,
        "voter_name": request.voterName,
        "option_id": request.optionId
    }
    supabase.table("votes").upsert(vote_data).execute()
    
    # 3. Check if all players have voted
    players_res = supabase.table("players").select("*").eq("room_id", room_id).order("created_at").execute()
    all_players = players_res.data
    
    votes_res = supabase.table("votes").select("voter_name, option_id").eq("room_id", room_id).execute()
    current_votes = votes_res.data
    
    # 4. If everyone (except the acting player) voted, trigger results
    # Threshold is num_players - 1 because active player doesn't vote for self
    if len(current_votes) >= len(all_players) - 1:
        return await _process_voting_results(room, current_votes, all_players)
    
    # Otherwise, just update phase to 'voting' if it was 'arguing'
    if room["phase"] == "arguing":
        supabase.table("rooms").update({"phase": "voting"}).eq("id", room_id).execute()
    
    return {"status": "vote_cast", "waitingFor": len(all_players) - len(current_votes)}

async def _process_voting_results(room, votes, all_players):
    room_id = room["id"]
    config = room.get("config", {})
    
    # 1. Get current case from config (Source of Truth) or root column (Fallback)
    case_id = config.get("current_case_id") or room.get("current_case_id")
    
    if not case_id:
        raise HTTPException(
            status_code=400, 
            detail="No active case found for this room. Ensure the player has reached a zone."
        )
    
    case_res = supabase.table("cases").select("*").eq("id", str(case_id)).execute()
    if not case_res.data:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    
    case = case_res.data[0]
    rubric = {r["id"]: r["points"] for r in case["rubric"]}
    
    # 2. Calculate Winner
    # If no votes, default to 0 points (shouldn't happen with threshold)
    if not votes:
        final_option = "none"
        points_earned = 0
    else:
        counts = {}
        for v in votes:
            opt = v["option_id"]
            counts[opt] = counts.get(opt, 0) + 1
        
        max_votes = max(counts.values())
        winners = [opt for opt, count in counts.items() if count == max_votes]
        
        final_option = winners[0]
        if len(winners) > 1:
            # Tie-breaker: choose option with more points in rubric
            final_option = max(winners, key=lambda opt: rubric.get(opt, 0))
        
        points_earned = rubric.get(final_option, 0)
    
    # 3. IDENTIFY ACTING PLAYER
    # The active player is the one whose turn it WAS
    current_turn_idx = room.get("current_turn_index", 0)
    # players were passed as all_players (ordered by created_at)
    acting_player = all_players[current_turn_idx]
    
    # 4. UPDATE PLAYER SCORE IN DB
    new_score = acting_player.get("score", 0) + points_earned
    supabase.table("players").update({"score": new_score}).eq("id", acting_player["id"]).execute()
    
    # 5. PREPARE NEXT TURN
    num_players = len(all_players)
    next_turn_idx = (current_turn_idx + 1) % num_players
    
    config = room.get("config", {})
    turn_history = config.get("turnHistory", [])
    
    new_turn = {
        "turnNumber": len(turn_history) + 1,
        "playerName": acting_player["name"],
        "diceValue": room.get("dice_value", 0),
        "caseId": str(room["current_case_id"]),
        "selectedOption": final_option,
        "pointsEarned": points_earned,
        "timestamp": str(datetime.now())
    }
    turn_history.append(new_turn)
    
    # Global completed turns
    curr_completed = config.get("completed_turns", 0)
    total_turns_limit = config.get("totalTurns", 10)
    
    is_finished = (curr_completed + 1) >= total_turns_limit
    new_status = "finished" if is_finished else "in_progress"
    new_phase = "finished" if is_finished else "rolling"
    
    # 6. ATOMIC UPDATE ROOM
    # Delete votes first
    supabase.table("votes").delete().eq("room_id", room_id).execute()
    
    update_data = {
        "status": new_status,
        "phase": new_phase,
        "current_turn_index": next_turn_idx,
        "current_zone_id": None,
        "current_argument": None,
        "current_case_id": None,
        "dice_value": None, # Reset dice for next player
        "config": {
            **config,
            "turnHistory": turn_history,
            "completed_turns": curr_completed + 1,
            "current_case_id": None,
            "current_case_data": None
        }
    }
    supabase.table("rooms").update(update_data).eq("id", room_id).execute()
    
    return {
        "status": "voting_completed",
        "winnerOption": final_option,
        "pointsEarned": points_earned,
        "nextPlayer": all_players[next_turn_idx]["name"]
    }

@router.get("/rooms/{roomCode}/vote-results")
async def get_vote_results(roomCode: str):
    room_res = supabase.table("rooms").select("*").eq("room_code", roomCode).execute()
    if not room_res.data:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room = room_res.data[0]
    config = room.get("config", {})
    turn_history = config.get("turnHistory", [])
    
    if not turn_history:
        return {"status": "no_results_yet"}
        
    last_turn = turn_history[-1]
    return {
        "winnerOption": last_turn.get("selectedOption"),
        "pointsEarned": last_turn.get("pointsEarned"),
        "isFinished": room["status"] == "finished"
    }

@router.post("/rooms/{roomCode}/reset")
async def reset_room(roomCode: str):
    # 1. Get room
    room_res = supabase.table("rooms").select("*").eq("room_code", roomCode).execute()
    if not room_res.data:
        raise HTTPException(status_code=404, detail="Room not found")
    
    room = room_res.data[0]
    room_id = room["id"]
    
    # 2. Update rooms table
    # Resetting status, phase, and the config JSONB (which stores turn history)
    config = room.get("config", {})
    new_config = config.copy()
    new_config["turnHistory"] = []
    new_config["current_turn_index"] = 0
    new_config["completed_turns"] = 0
    
    update_room_data = {
        "status": "waiting",
        "phase": "rolling",
        "dice_value": None,
        "current_argument": None,
        "current_case_id": None,
        "current_zone_id": None,
        "config": new_config
    }
    
    supabase.table("rooms").update(update_room_data).eq("id", room_id).execute()
    
    # 3. Update players table
    # Only resetting current_position since score and turns_played are calculated from turnHistory
    initial_position = {"nodeId": "park", "edgeId": None, "edgeProgress": 0}
    supabase.table("players").update({
        "current_position": initial_position
    }).eq("room_id", room_id).execute()
    
    return {
        "status": "success",
        "message": f"Room {roomCode} has been reset to initial state."
    }

