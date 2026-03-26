from enum import Enum


class RoomStatus(str, Enum):
    """Lifecycle status of a room (lobby → game → end)."""
    WAITING = "waiting"
    IN_PROGRESS = "in_progress"
    PLAYING = "playing"
    FINISHED = "finished"


class GamePhase(str, Enum):
    """Fine-grained phase within a single turn."""
    ROLLING = "rolling"
    MOVING = "moving"
    ARGUING = "arguing"
    VOTING = "voting"
    FINISHED = "finished"
