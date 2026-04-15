"""
game_service.py
---------------
Pure business logic for the Conversex game loop.
All functions are importable and testable without a running FastAPI server or live Supabase connection.
"""
from __future__ import annotations

import random
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException

from app.enums import GamePhase, RoomStatus
from app.schemas.schemas import BoardPosition, CaseResponse, RubricOption

# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────

# Maps board zone node IDs → cases.zone integer in the DB
ZONE_MAP: Dict[str, int] = {
    "hospital": 1,
    "wifi": 2,
    "home": 3,
    "neighborhood": 4,
    "school": 5,
}

# Dice range (inclusive). Board edge distances range from 3 to 11,
# so a 1–6 die gives short hops while 1–12 spans the whole board.
DICE_MIN = 18
DICE_MAX = 20


# ─────────────────────────────────────────────
# Turn index helpers
# ─────────────────────────────────────────────

def calculate_turn_index(turn_history: List[Any], num_players: int) -> int:
    """Derive the current player index from turn history length."""
    if num_players == 0:
        return 0
    return len(turn_history) % num_players


def roll_dice() -> int:
    """Generate a random dice value in the configured range."""
    return random.randint(DICE_MIN, DICE_MAX)


# ─────────────────────────────────────────────
# Case selection
# ─────────────────────────────────────────────

def pick_case_for_zone(zone_id: str, supabase) -> Optional[Dict[str, Any]]:
    """
    Fetch a random case for the given zone from the DB.
    Filters out cases with empty descriptions.
    Falls back to any valid case if none found for the specific zone.
    Returns None if the cases table is empty or no valid cases found.
    """
    zone_number = ZONE_MAP.get(zone_id, 1)
    case_res = supabase.table("cases").select("*").eq("zone", zone_number).neq("description", "").execute()

    if not case_res.data:
        # Fallback: grab all available valid cases
        case_res = supabase.table("cases").select("*").neq("description", "").execute()

    if not case_res.data:
        return None

    return random.choice(case_res.data)


def build_case_response(case: Dict[str, Any]) -> CaseResponse:
    """Convert a raw DB case row into a typed CaseResponse."""
    return CaseResponse(
        caseId=case["id"],
        description=case["description"],
        rubric=[RubricOption(**r) for r in case["rubric"]],
    )


# ─────────────────────────────────────────────
# Turn advancement
# ─────────────────────────────────────────────

def build_turn_record(
    turn_history: List[Any],
    player_name: str,
    dice_value: int,
    case_id: str = "none",
    selected_option: Optional[str] = None,
    points_earned: int = 0,
    feedback: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Build the dict that gets appended to config['turnHistory']."""
    return {
        "turnNumber": len(turn_history) + 1,
        "playerName": player_name,
        "diceValue": dice_value,
        "caseId": case_id,
        "selectedOption": selected_option,
        "feedback": feedback or {},
        "pointsEarned": points_earned,
        "timestamp": datetime.now().isoformat(),
    }


def advance_turn_config(
    config: Dict[str, Any],
    new_turn: Dict[str, Any],
    num_players: int,
) -> Tuple[Dict[str, Any], bool]:
    """
    Append new_turn to config['turnHistory'], advance current_turn_index,
    update completed_turns, and determine if the game is finished.

    Returns:
        (updated_config, is_finished)
    """
    new_config = config.copy()
    turn_history = list(config.get("turnHistory", []))
    turn_history.append(new_turn)

    total_turns: int = config.get("totalTurns", 10)
    current_index: int = config.get("current_turn_index", len(turn_history) % max(num_players, 1))
    curr_completed: int = config.get("completed_turns", 0)

    next_index = (current_index + 1) % max(num_players, 1)
    new_completed = curr_completed + (1 if next_index == 0 else 0)
    is_finished = len(turn_history) >= (total_turns * max(num_players, 1))

    new_config["turnHistory"] = turn_history
    new_config["current_turn_index"] = next_index
    new_config["completed_turns"] = new_completed
    # Clear case state for next turn
    new_config["current_case_id"] = None
    new_config["current_case_data"] = None

    return new_config, is_finished


# ─────────────────────────────────────────────
# Voting
# ─────────────────────────────────────────────

def tally_votes(votes: List[Dict[str, Any]], rubric: Dict[str, int]) -> Tuple[str, int]:
    """
    Count votes and determine winning option.
    Tie-breaker: choose the option with the highest rubric points.

    Args:
        votes: list of {"voter_name": str, "option_id": str}
        rubric: {option_id: points}

    Returns:
        (winning_option_id, points_earned)
    """
    if not votes:
        return "none", 0

    counts: Dict[str, int] = {}
    for v in votes:
        opt = v["option_id"]
        counts[opt] = counts.get(opt, 0) + 1

    max_votes = max(counts.values())
    winners = [opt for opt, count in counts.items() if count == max_votes]

    final_option = winners[0]
    if len(winners) > 1:
        # Tie-breaker: highest rubric points
        final_option = max(winners, key=lambda opt: rubric.get(opt, 0))

    return final_option, rubric.get(final_option, 0)


async def process_voting_results(
    room: Dict[str, Any],
    votes: List[Dict[str, Any]],
    all_players: List[Dict[str, Any]],
    supabase,
) -> Dict[str, Any]:
    """
    Full voting resolution pipeline:
      1. Load case + rubric from DB
      2. Tally votes → winning option + points
      3. Update acting player's score in DB
      4. Advance turn (config + room update)
      5. Clear votes for next round

    Returns the JSON response for the /vote endpoint.
    """
    room_id = room["id"]
    config = room.get("config", {})

    # ── 1. Identify acting player ──────────────────────────────────────────
    # Source of truth: config["current_turn_index"]  (NOT a root column)
    current_turn_idx: int = config.get("current_turn_index", 0)
    num_players = len(all_players)

    if num_players == 0:
        raise HTTPException(status_code=400, detail="No players found in room.")

    acting_player = all_players[current_turn_idx % num_players]

    # ── 2. Load case ───────────────────────────────────────────────────────
    case_id = config.get("current_case_id") or room.get("current_case_id")
    if not case_id:
        raise HTTPException(
            status_code=400,
            detail="No active case found for this room. Ensure the player has reached a zone.",
        )

    case_res = supabase.table("cases").select("*").eq("id", str(case_id)).execute()
    if not case_res.data:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")

    case = case_res.data[0]
    rubric: Dict[str, int] = {r["id"]: r["points"] for r in case["rubric"]}

    # ── 3. Tally votes ────────────────────────────────────────────────────
    final_option, points_earned = tally_votes(votes, rubric)

    # ── 4. Update acting player score ─────────────────────────────────────
    new_score = (acting_player.get("score") or 0) + points_earned
    supabase.table("players").update({
        "score": new_score,
        "turns_played": (acting_player.get("turns_played") or 0) + 1,
    }).eq("id", acting_player["id"]).execute()

    # ── 5. Build new turn record and advance config ────────────────────────
    new_turn = build_turn_record(
        turn_history=config.get("turnHistory", []),
        player_name=acting_player["name"],
        dice_value=room.get("dice_value") or 0,
        case_id=str(room.get("current_case_id", case_id)),
        selected_option=final_option,
        points_earned=points_earned,
    )

    turn_history = config.get("turnHistory", [])
    total_turns: int = config.get("totalTurns", 10)
    updated_config, is_finished = advance_turn_config(config, new_turn, num_players)
    next_turn_idx: int = updated_config["current_turn_index"]

    new_status = RoomStatus.FINISHED if is_finished else RoomStatus.IN_PROGRESS
    new_phase = GamePhase.FINISHED if is_finished else GamePhase.ROLLING

    # ── 6. Delete votes & update room atomically ───────────────────────────
    supabase.table("votes").delete().eq("room_id", room_id).execute()

    supabase.table("rooms").update({
        "status": new_status.value,
        "phase": new_phase.value,
        "current_zone_id": None,
        "current_argument": None,
        "current_case_id": None,
        "dice_value": None,
        "config": updated_config,
    }).eq("id", room_id).execute()

    return {
        "status": "voting_completed",
        "winnerOption": final_option,
        "pointsEarned": points_earned,
        "nextPlayer": all_players[next_turn_idx % num_players]["name"],
    }
