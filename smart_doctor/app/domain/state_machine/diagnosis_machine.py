class InvalidTransitionError(Exception):
    pass


class DiagnosisStateMachine:
    TRANSITIONS = {
        "collecting": {
            "symptom_complete": "analyzing",
            "user_chitchat": "collecting",
            "need_more_info": "collecting",
        },
        "analyzing": {
            "need_more_info": "collecting",
            "ready_to_recommend": "recommending",
            "user_chitchat": "analyzing",
            "symptom_complete": "analyzing",
        },
        "recommending": {
            "user_confirmed": "completed",
            "user_dissatisfied": "collecting",
            "user_chitchat": "recommending",
            "need_more_info": "collecting",
        },
        "completed": {
            "new_symptom": "collecting",
            "user_chitchat": "completed",
        },
    }

    def __init__(self, initial_state: str = "collecting"):
        self._state = initial_state

    @property
    def state(self) -> str:
        return self._state

    def can_transition(self, event: str) -> bool:
        return event in self.TRANSITIONS.get(self._state, {})

    def transition(self, event: str) -> str:
        if not self.can_transition(event):
            raise InvalidTransitionError(
                f"Cannot transition from '{self._state}' with event '{event}'"
            )
        self._state = self.TRANSITIONS[self._state][event]
        return self._state

    def intent_to_event(self, intent: str, current_state: str) -> str:
        INTENT_MAP = {
            "new_symptom": "symptom_complete" if current_state == "collecting" else "new_symptom",
            "follow_up_answer": "symptom_complete",
            "need_detail": "need_more_info",
            "ready_recommend": "ready_to_recommend",
            "confirm": "user_confirmed",
            "dissatisfied": "user_dissatisfied",
            "chitchat": "user_chitchat",
        }
        return INTENT_MAP.get(intent, "need_more_info")
