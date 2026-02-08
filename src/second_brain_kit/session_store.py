"""In-memory session store: channel → Claude session mapping + cost tracking."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Session:
    session_id: str | None = None
    model: str = "sonnet"
    system_prompt: str | None = None
    total_cost_usd: float = 0.0
    turn_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    last_used: datetime = field(default_factory=datetime.now)
    history: list[tuple[str, str]] = field(default_factory=list)


class SessionStore:
    """Maps channel IDs to Claude sessions."""

    def __init__(self, default_model: str = "sonnet") -> None:
        self._sessions: dict[int, Session] = {}
        self._default_model = default_model

    def get(self, channel_id: int) -> Session:
        if channel_id not in self._sessions:
            self._sessions[channel_id] = Session(model=self._default_model)
        return self._sessions[channel_id]

    def reset(self, channel_id: int) -> None:
        self._sessions.pop(channel_id, None)

    def set_model(self, channel_id: int, model: str) -> None:
        self.get(channel_id).model = model

    def set_system_prompt(self, channel_id: int, prompt: str | None) -> None:
        self.get(channel_id).system_prompt = prompt

    def update_after_response(
        self, channel_id: int, session_id: str, cost_usd: float
    ) -> None:
        session = self.get(channel_id)
        session.session_id = session_id
        session.total_cost_usd += cost_usd
        session.turn_count += 1
        session.last_used = datetime.now()

    def add_history(self, channel_id: int, user_msg: str, bot_msg: str) -> None:
        self.get(channel_id).history.append((user_msg[:200], bot_msg))

    def total_cost(self) -> float:
        return sum(s.total_cost_usd for s in self._sessions.values())

    def all_sessions(self) -> dict[int, Session]:
        return dict(self._sessions)
