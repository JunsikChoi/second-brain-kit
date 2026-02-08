"""Tests for session_store module."""

from second_brain_kit.session_store import Session, SessionStore


class TestSession:
    def test_defaults(self) -> None:
        s = Session()
        assert s.session_id is None
        assert s.model == "sonnet"
        assert s.system_prompt is None
        assert s.total_cost_usd == 0.0
        assert s.turn_count == 0
        assert s.history == []


class TestSessionStore:
    def test_get_creates_new_session(self) -> None:
        store = SessionStore()
        s = store.get(100)
        assert isinstance(s, Session)
        assert s.model == "sonnet"

    def test_get_returns_same_session(self) -> None:
        store = SessionStore()
        s1 = store.get(100)
        s2 = store.get(100)
        assert s1 is s2

    def test_default_model(self) -> None:
        store = SessionStore(default_model="opus")
        s = store.get(100)
        assert s.model == "opus"

    def test_reset_removes_session(self) -> None:
        store = SessionStore()
        store.get(100)
        store.reset(100)
        # get() after reset should create a fresh session
        s = store.get(100)
        assert s.turn_count == 0

    def test_reset_nonexistent_channel(self) -> None:
        store = SessionStore()
        store.reset(999)  # Should not raise

    def test_set_model(self) -> None:
        store = SessionStore()
        store.set_model(100, "haiku")
        assert store.get(100).model == "haiku"

    def test_set_system_prompt(self) -> None:
        store = SessionStore()
        store.set_system_prompt(100, "Be helpful")
        assert store.get(100).system_prompt == "Be helpful"

    def test_set_system_prompt_none(self) -> None:
        store = SessionStore()
        store.set_system_prompt(100, "Something")
        store.set_system_prompt(100, None)
        assert store.get(100).system_prompt is None

    def test_update_after_response(self) -> None:
        store = SessionStore()
        store.update_after_response(100, "sess-1", 0.05)
        s = store.get(100)
        assert s.session_id == "sess-1"
        assert s.total_cost_usd == 0.05
        assert s.turn_count == 1

    def test_update_accumulates_cost(self) -> None:
        store = SessionStore()
        store.update_after_response(100, "sess-1", 0.05)
        store.update_after_response(100, "sess-1", 0.10)
        s = store.get(100)
        assert abs(s.total_cost_usd - 0.15) < 1e-9
        assert s.turn_count == 2

    def test_add_history(self) -> None:
        store = SessionStore()
        store.add_history(100, "hello", "world")
        s = store.get(100)
        assert len(s.history) == 1
        assert s.history[0] == ("hello", "world")

    def test_add_history_truncates_user_msg(self) -> None:
        store = SessionStore()
        long_msg = "x" * 300
        store.add_history(100, long_msg, "ok")
        s = store.get(100)
        assert len(s.history[0][0]) == 200

    def test_total_cost_across_channels(self) -> None:
        store = SessionStore()
        store.update_after_response(100, "s1", 0.10)
        store.update_after_response(200, "s2", 0.20)
        assert abs(store.total_cost() - 0.30) < 1e-9

    def test_all_sessions(self) -> None:
        store = SessionStore()
        store.get(100)
        store.get(200)
        sessions = store.all_sessions()
        assert set(sessions.keys()) == {100, 200}
