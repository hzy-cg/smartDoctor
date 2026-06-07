import pytest
from app.domain.state_machine import DiagnosisStateMachine, InvalidTransitionError


class TestDiagnosisStateMachine:

    def test_initial_state_is_collecting(self):
        sm = DiagnosisStateMachine()
        assert sm.state == "collecting"

    def test_symptom_complete_transitions_to_analyzing(self):
        sm = DiagnosisStateMachine()
        sm.transition("symptom_complete")
        assert sm.state == "analyzing"

    def test_need_more_info_back_to_collecting(self):
        sm = DiagnosisStateMachine()
        sm.transition("symptom_complete")
        assert sm.state == "analyzing"
        sm.transition("need_more_info")
        assert sm.state == "collecting"

    def test_ready_to_recommend(self):
        sm = DiagnosisStateMachine()
        sm.transition("symptom_complete")
        sm.transition("ready_to_recommend")
        assert sm.state == "recommending"

    def test_user_confirmed_to_completed(self):
        sm = DiagnosisStateMachine()
        sm.transition("symptom_complete")
        sm.transition("ready_to_recommend")
        sm.transition("user_confirmed")
        assert sm.state == "completed"

    def test_user_dissatisfied_back_to_collecting(self):
        sm = DiagnosisStateMachine()
        sm.transition("symptom_complete")
        sm.transition("ready_to_recommend")
        sm.transition("user_dissatisfied")
        assert sm.state == "collecting"

    def test_new_symptom_from_completed(self):
        sm = DiagnosisStateMachine()
        sm.transition("symptom_complete")
        sm.transition("ready_to_recommend")
        sm.transition("user_confirmed")
        sm.transition("new_symptom")
        assert sm.state == "collecting"

    def test_invalid_transition_raises(self):
        sm = DiagnosisStateMachine()
        with pytest.raises(InvalidTransitionError):
            sm.transition("ready_to_recommend")

    def test_can_transition_returns_bool(self):
        sm = DiagnosisStateMachine()
        assert sm.can_transition("symptom_complete") is True
        assert sm.can_transition("user_chitchat") is True
        assert sm.can_transition("ready_to_recommend") is False

    def test_chitchat_stays_in_collecting(self):
        sm = DiagnosisStateMachine()
        sm.transition("user_chitchat")
        assert sm.state == "collecting"

    def test_intent_to_event_mapping(self):
        sm = DiagnosisStateMachine()
        assert sm.intent_to_event("new_symptom", "collecting") == "symptom_complete"
        assert sm.intent_to_event("follow_up_answer", "collecting") == "symptom_complete"
        assert sm.intent_to_event("need_detail", "analyzing") == "need_more_info"
        assert sm.intent_to_event("ready_recommend", "analyzing") == "ready_to_recommend"
        assert sm.intent_to_event("confirm", "recommending") == "user_confirmed"

    def test_full_diagnosis_flow(self):
        sm = DiagnosisStateMachine()
        assert sm.state == "collecting"

        sm.transition("symptom_complete")
        assert sm.state == "analyzing"

        sm.transition("need_more_info")
        assert sm.state == "collecting"

        sm.transition("symptom_complete")
        assert sm.state == "analyzing"

        sm.transition("ready_to_recommend")
        assert sm.state == "recommending"

        sm.transition("user_confirmed")
        assert sm.state == "completed"
