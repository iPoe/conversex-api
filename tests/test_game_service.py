"""
tests/test_game_service.py
--------------------------
Pure unit tests for game_service.py.
No FastAPI server, no Supabase connection needed.
Run with: python3 -m pytest tests/test_game_service.py -v
"""
import pytest
from unittest.mock import MagicMock

from app.services.game_service import (
    calculate_turn_index,
    tally_votes,
    build_turn_record,
    advance_turn_config,
    roll_dice,
    DICE_MIN,
    DICE_MAX,
)


# ─────────────────────────────────────────────
# calculate_turn_index
# ─────────────────────────────────────────────

class TestCalculateTurnIndex:
    def test_empty_history_returns_zero(self):
        assert calculate_turn_index([], 2) == 0

    def test_first_player_goes_first(self):
        history = [{"turnNumber": 1}]  # 1 completed turn
        assert calculate_turn_index(history, 2) == 1  # now player 2's turn

    def test_wraps_around(self):
        # 2 turns for 2 players → back to player 0
        history = [{"turnNumber": 1}, {"turnNumber": 2}]
        assert calculate_turn_index(history, 2) == 0

    def test_single_player(self):
        history = [{"turnNumber": 1}, {"turnNumber": 2}]
        assert calculate_turn_index(history, 1) == 0

    def test_zero_players_returns_zero(self):
        assert calculate_turn_index([], 0) == 0


# ─────────────────────────────────────────────
# tally_votes
# ─────────────────────────────────────────────

class TestTallyVotes:
    def test_no_votes(self):
        option, points = tally_votes([], {"A": 5, "B": 3})
        assert option == "none"
        assert points == 0

    def test_unanimous_vote(self):
        votes = [{"option_id": "A"}, {"option_id": "A"}]
        option, points = tally_votes(votes, {"A": 5, "B": 3})
        assert option == "A"
        assert points == 5

    def test_majority_vote(self):
        votes = [{"option_id": "A"}, {"option_id": "A"}, {"option_id": "B"}]
        option, points = tally_votes(votes, {"A": 5, "B": 3})
        assert option == "A"
        assert points == 5

    def test_tie_broken_by_rubric_points(self):
        # A and B tied → B has more points → B wins
        votes = [{"option_id": "A"}, {"option_id": "B"}]
        option, points = tally_votes(votes, {"A": 3, "B": 5})
        assert option == "B"
        assert points == 5

    def test_option_not_in_rubric_gives_zero_points(self):
        votes = [{"option_id": "X"}]
        option, points = tally_votes(votes, {"A": 5})
        assert option == "X"
        assert points == 0


# ─────────────────────────────────────────────
# roll_dice
# ─────────────────────────────────────────────

class TestRollDice:
    def test_roll_is_in_range(self):
        for _ in range(50):
            val = roll_dice()
            assert DICE_MIN <= val <= DICE_MAX, f"Dice value {val} out of range [{DICE_MIN}, {DICE_MAX}]"


# ─────────────────────────────────────────────
# build_turn_record
# ─────────────────────────────────────────────

class TestBuildTurnRecord:
    def test_turn_number_is_next(self):
        history = [{"turnNumber": 1}, {"turnNumber": 2}]
        record = build_turn_record(history, "Alice", 4)
        assert record["turnNumber"] == 3

    def test_defaults(self):
        record = build_turn_record([], "Bob", 6)
        assert record["playerName"] == "Bob"
        assert record["diceValue"] == 6
        assert record["caseId"] == "none"
        assert record["selectedOption"] is None
        assert record["pointsEarned"] == 0
        assert "timestamp" in record


# ─────────────────────────────────────────────
# advance_turn_config
# ─────────────────────────────────────────────

class TestAdvanceTurnConfig:
    def _base_config(self, turn_history=None):
        return {
            "totalTurns": 4,
            "turnHistory": turn_history or [],
            "current_turn_index": 0,
            "completed_turns": 0,
        }

    def test_turn_index_advances(self):
        config = self._base_config()
        new_turn = build_turn_record([], "Alice", 3)
        updated, is_finished = advance_turn_config(config, new_turn, 2)
        assert updated["current_turn_index"] == 1
        assert not is_finished

    def test_turn_index_wraps(self):
        config = self._base_config([{"t": 1}])  # 1 turn already done, index was 1
        config["current_turn_index"] = 1
        new_turn = build_turn_record(config["turnHistory"], "Bob", 5)
        updated, _ = advance_turn_config(config, new_turn, 2)
        assert updated["current_turn_index"] == 0

    def test_finished_when_total_turns_reached(self):
        history = [{"t": i} for i in range(3)]  # 3 of 4 done
        config = self._base_config(history)
        new_turn = build_turn_record(history, "Alice", 4)
        updated, is_finished = advance_turn_config(config, new_turn, 2)
        assert is_finished

    def test_case_state_cleared(self):
        config = self._base_config()
        config["current_case_id"] = "some-uuid"
        config["current_case_data"] = {"foo": "bar"}
        new_turn = build_turn_record([], "Alice", 2)
        updated, _ = advance_turn_config(config, new_turn, 2)
        assert updated["current_case_id"] is None
        assert updated["current_case_data"] is None
