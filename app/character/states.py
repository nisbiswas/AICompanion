from enum import Enum


class CharacterState(str, Enum):

    IDLE = "IDLE"
    RUN = "RUN"
    SITTING = "SITTING"
    TAUNT = "TAUNT"
    ATTACK = "ATTACK"