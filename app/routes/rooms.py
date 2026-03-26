from fastapi import APIRouter, HTTPException
from app.schemas.schemas import (
    RoomCreateRequest, RoomResponse, PlayerJoinRequest,
    PlayerResponse, GameStartRequest, LiveGameState, TurnRecord,
    RollDiceRequest, RollDiceResponse, BoardPosition, MoveRequest,
    MoveResponse, ArgumentRequest, CaseResponse, VoteRequest
)
from app.enums import RoomStatus, GamePhase
from app.services.game_service import (
    roll_dice,
    calculate_turn_index,
    pick_case_for_zone,
    build_case_response,
    build_turn_record,
    advance_turn_config,
    process_voting_results,
)
from core.database import supabase
from core.board import move_player, BOARD_NODES, get_outgoing_edges
import random
import string
from uuid import UUID
from datetime import datetime

router = APIRouter()


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def generate_room_code() -> str:
    """Generate a unique 6-character alphanumeric room code."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


def _build_player_response(p: dict) -> PlayerResponse:
    return PlayerResponse(
        name=p["name"],
        avatar=p["avatar_id"],
        isHost=p["is_host"],
        boardPosition=BoardPosition(**p["current_position"]),
        score=p.get("score") or 0,
        turnsPlayed=p.get("turns_played") or 0,
    )


INITIAL_POSITION = {"nodeId": "park", "edgeId": None, "edgeProgress": 0}


# ─────────────────────────────────────────────
# Lobby Endpoints
# ─────────────────────────────────────────────

@router.post("/rooms", response_model=RoomResponse)
async def create_room(request: RoomCreateRequest):
    room_code = generate_room_code()

    # 1. Create room in DB
    room_data = {
        "room_code": room_code,
        "status": RoomStatus.WAITING.value,
        "phase": GamePhase.ROLLING.value,
        "config": {
            "totalTurns": 10,
            "pointsToWin": 40,
            "isTimerEnabled": False,
        },
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
        "current_position": INITIAL_POSITION,
    }
    player_res = supabase.table("players").insert(player_data).execute()
    if not player_res.data:
        raise HTTPException(status_code=500, detail="Error creating host player")
    host = player_res.data[0]

    return RoomResponse(
        roomCode=room["room_code"],
        gameId=room["id"],
        status=room["status"],
        phase=room["phase"],
        players=[_build_player_response(host)],
        currentArgument=room.get("current_argument"),
    )


@router.post("/rooms/{roomCode}/join", response_model=RoomResponse)
async def join_room(roomCode: str, request: PlayerJoinRequest):
    # 1. Get room
    room_res = supabase.table("rooms").select("*").eq("room_code", roomCode).execute()
    if not room_res.data:
        raise HTTPException(status_code=404, detail="Room not found")
    room = room_res.data[0]

    # 2. Check capacity
    players_res = supabase.table("players").select("*").eq("room_id", room["id"]).execute()
    if len(players_res.data) >= 2:
        raise HTTPException(status_code=400, detail="Room is full")

    # 3. Add new player
    supabase.table("players").insert({
        "room_id": room["id"],
        "name": request.playerName,
        "avatar_id": request.playerAvatar,
        "is_host": False,
        "current_position": INITIAL_POSITION,
    }).execute()

    # 4. Return updated list
    updated = supabase.table("players").select("*").eq("room_id", room["id"]).execute()
    players_list = [_build_player_response(p) for p in updated.data]

    return RoomResponse(
        roomCode=room["room_code"],
        gameId=room["id"],
        status=room["status"],
        phase=room["phase"],
        players=players_list,
        currentArgument=room.get("current_argument"),
    )


@router.post("/rooms/{roomCode}/start", response_model=LiveGameState)
async def start_game(roomCode: str, request: GameStartRequest):
    # 1. Get room
    room_res = supabase.table("rooms").select("*").eq("room_code", roomCode).execute()
    if not room_res.data:
        raise HTTPException(status_code=404, detail="Room not found")
    room = room_res.data[0]

    # 2. Update room
    update_data = {
        "status": RoomStatus.IN_PROGRESS.value,
        "phase": GamePhase.ROLLING.value,
        "config": {
            "totalTurns": request.totalTurns,
            "pointsToWin": request.pointsToWin,
            "isTimerEnabled": request.isTimerEnabled,
            "turnHistory": [],
            "current_turn_index": 0,
            "completed_turns": 0,
        },
    }
    updated_room_res = supabase.table("rooms").update(update_data).eq("id", room["id"]).execute()
    updated_room = updated_room_res.data[0]

    # 3. Get players
    players_res = supabase.table("players").select("*").eq("room_id", room["id"]).order("created_at").execute()
    players_list = [_build_player_response(p) for p in players_res.data]

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
        currentArgument=None,
    )


@router.get("/rooms/{roomCode}", response_model=LiveGameState)
async def get_room_state(roomCode: str):
    # 1. Get room
    room_res = supabase.table("rooms").select("*").eq("room_code", roomCode).execute()
    if not room_res.data:
        raise HTTPException(status_code=404, detail="Room not found")
    room = room_res.data[0]
    config = room.get("config", {})
    turn_history = config.get("turnHistory", [])

    # 2. Get players (ordered for consistent turn tracking)
    players_res = supabase.table("players").select("*").eq("room_id", room["id"]).order("created_at").execute()
    players_list = [_build_player_response(p) for p in players_res.data]

    current_turn_index = calculate_turn_index(turn_history, len(players_list))

    return LiveGameState(
        gameId=room["id"],
        roomCode=room["room_code"],
        status=room["status"],
        phase=room["phase"],
        currentTurnIndex=current_turn_index,
        totalTurns=config.get("totalTurns", 10),
        pointsToWin=config.get("pointsToWin", 40),
        players=players_list,
        turnHistory=[TurnRecord(**t) for t in turn_history],
        currentCaseId=room.get("current_case_id"),
        currentArgument=room.get("current_argument"),
    )


# ─────────────────────────────────────────────
# Game-Loop Endpoints
# ─────────────────────────────────────────────

@router.post("/rooms/{roomCode}/roll", response_model=RollDiceResponse)
async def roll_dice_route(roomCode: str, request: RollDiceRequest):
    # 1. Get room
    room_res = supabase.table("rooms").select("*").eq("room_code", roomCode).execute()
    if not room_res.data:
        raise HTTPException(status_code=404, detail="Room not found")
    room = room_res.data[0]
    config = room.get("config", {})
    turn_history = config.get("turnHistory", [])

    # 2. Validate turn
    players_res = supabase.table("players").select("*").eq("room_id", room["id"]).order("created_at").execute()
    players = players_res.data
    if players:
        current_turn_index = calculate_turn_index(turn_history, len(players))
        if players[current_turn_index]["name"] != request.playerName:
            raise HTTPException(
                status_code=403,
                detail=f"It's not {request.playerName}'s turn. It's {players[current_turn_index]['name']}'s turn.",
            )

    # 3. Roll and persist
    dice_value = roll_dice()
    supabase.table("rooms").update({"dice_value": dice_value}).eq("id", room["id"]).execute()

    return RollDiceResponse(diceValue=dice_value)


@router.post("/rooms/{roomCode}/move", response_model=MoveResponse)
async def move_player_route(roomCode: str, request: MoveRequest):
    # 1. Get room and player
    room_res = supabase.table("rooms").select("*").eq("room_code", roomCode).execute()
    if not room_res.data:
        raise HTTPException(status_code=404, detail="Room not found")
    room = room_res.data[0]

    player_res = (
        supabase.table("players")
        .select("*")
        .eq("room_id", room["id"])
        .eq("name", request.playerName)
        .execute()
    )
    if not player_res.data:
        raise HTTPException(status_code=404, detail="Player not found")
    player = player_res.data[0]

    # 2. Validate turn
    players_res = supabase.table("players").select("*").eq("room_id", room["id"]).order("created_at").execute()
    all_players = players_res.data
    config = room.get("config", {})
    turn_history = config.get("turnHistory", [])

    if all_players:
        current_turn_index = calculate_turn_index(turn_history, len(all_players))
        if all_players[current_turn_index]["name"] != request.playerName:
            raise HTTPException(
                status_code=403,
                detail=f"It's not {request.playerName}'s turn.",
            )

    # 3. Execute movement
    current_pos = BoardPosition(**player["current_position"])
    move_result = move_player(current_pos, request.diceValue, request.choiceEdgeId)
    new_pos = move_result["newPosition"]

    new_config = config.copy()
    new_config["last_action_by"] = request.playerName
    new_config["branch_choice"] = request.choiceEdgeId

    new_phase = GamePhase.ROLLING
    new_zone_id = None
    new_dice_value = room.get("dice_value")
    new_status = room.get("status", RoomStatus.IN_PROGRESS.value)
    case_response = None

    if move_result["status"] == "waiting_choice":
        new_phase = GamePhase.MOVING

    elif move_result["status"] == "zone_reached":
        new_phase = GamePhase.ARGUING
        new_zone_id = move_result["zoneId"]
        new_dice_value = None

        case = pick_case_for_zone(new_zone_id, supabase)
        if case:
            new_config["current_case_id"] = case["id"]
            new_config["current_case_data"] = case
            case_response = build_case_response(case)

    else:
        # Finished on a normal tile → advance turn
        new_phase = GamePhase.ROLLING
        new_dice_value = None

        new_turn = build_turn_record(
            turn_history=turn_history,
            player_name=request.playerName,
            dice_value=request.diceValue,
        )
        new_config, is_finished = advance_turn_config(new_config, new_turn, len(all_players))

        if is_finished:
            new_status = RoomStatus.FINISHED.value
            new_phase = GamePhase.FINISHED

    # 4. Atomic update via RPC
    try:
        supabase.rpc("commit_player_move", {
            "p_room_id": str(room["id"]),
            "p_player_id": str(player["id"]),
            "p_new_position": new_pos.dict(),
            "p_new_phase": new_phase.value,
            "p_new_dice_value": new_dice_value,
            "p_new_zone_id": new_zone_id,
            "p_new_config": new_config,
            "p_new_status": new_status,
        }).execute()

        # Sync root columns that RPC doesn't handle
        extra_updates = {}
        if new_dice_value is None:
            extra_updates["dice_value"] = None
        if new_config.get("current_case_id"):
            extra_updates["current_case_id"] = new_config["current_case_id"]
        if extra_updates:
            supabase.table("rooms").update(extra_updates).eq("id", room["id"]).execute()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Atomic update failed: {str(e)}")

    return MoveResponse(
        newPosition=new_pos,
        remainingSteps=move_result["remainingSteps"],
        status=move_result["status"],
        options=move_result.get("options"),
        zoneId=move_result.get("zoneId"),
        caseData=case_response,
    )


@router.post("/rooms/{roomCode}/argue")
async def submit_argument(roomCode: str, request: ArgumentRequest):
    room_res = supabase.table("rooms").select("*").eq("room_code", roomCode).execute()
    if not room_res.data:
        raise HTTPException(status_code=404, detail="Room not found")
    room = room_res.data[0]

    supabase.table("rooms").update({
        "current_argument": request.argument,
        "phase": GamePhase.VOTING.value,
    }).eq("id", room["id"]).execute()

    return {"status": "argument_submitted"}


@router.post("/rooms/{roomCode}/vote")
async def cast_vote(roomCode: str, request: VoteRequest):
    room_res = supabase.table("rooms").select("*").eq("room_code", roomCode).execute()
    if not room_res.data:
        raise HTTPException(status_code=404, detail="Room not found")
    room = room_res.data[0]
    room_id = room["id"]

    # Upsert vote (one per player per room)
    supabase.table("votes").upsert({
        "room_id": room_id,
        "voter_name": request.voterName,
        "option_id": request.optionId,
    }).execute()

    players_res = supabase.table("players").select("*").eq("room_id", room_id).order("created_at").execute()
    all_players = players_res.data

    votes_res = supabase.table("votes").select("voter_name, option_id").eq("room_id", room_id).execute()
    current_votes = votes_res.data

    # All non-acting players have voted → process results
    if len(current_votes) >= len(all_players) - 1:
        return await process_voting_results(room, current_votes, all_players, supabase)

    # Not everyone voted yet
    if room["phase"] == GamePhase.ARGUING.value:
        supabase.table("rooms").update({"phase": GamePhase.VOTING.value}).eq("id", room_id).execute()

    return {"status": "vote_cast", "waitingFor": len(all_players) - len(current_votes)}


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
        "isFinished": room["status"] == RoomStatus.FINISHED.value,
    }


@router.post("/rooms/{roomCode}/reset")
async def reset_room(roomCode: str):
    room_res = supabase.table("rooms").select("*").eq("room_code", roomCode).execute()
    if not room_res.data:
        raise HTTPException(status_code=404, detail="Room not found")
    room = room_res.data[0]
    room_id = room["id"]

    config = room.get("config", {})
    new_config = config.copy()
    new_config["turnHistory"] = []
    new_config["current_turn_index"] = 0
    new_config["completed_turns"] = 0
    new_config["current_case_id"] = None
    new_config["current_case_data"] = None

    supabase.table("rooms").update({
        "status": RoomStatus.WAITING.value,
        "phase": GamePhase.ROLLING.value,
        "dice_value": None,
        "current_argument": None,
        "current_case_id": None,
        "current_zone_id": None,
        "config": new_config,
    }).eq("id", room_id).execute()

    supabase.table("players").update({
        "current_position": INITIAL_POSITION,
        "score": 0,
        "turns_played": 0,
    }).eq("room_id", room_id).execute()

    return {"status": "success", "message": f"Room {roomCode} has been reset to initial state."}
