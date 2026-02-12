"""Tests for the Session data class."""

from __future__ import annotations

import datetime

from vault_mcp_agents.auth.session import Session


class TestSession:
    def test_not_expired_when_fresh(self, operator_session: Session) -> None:
        assert not operator_session.is_expired

    def test_expired_when_ttl_exceeded(self) -> None:
        session = Session(
            human_id="test",
            human_role="viewer",
            vault_token="s.expired",
            token_policies=frozenset(),
            created_at=datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=2),
            ttl_seconds=60,
        )
        assert session.is_expired

    def test_immutable(self, operator_session: Session) -> None:
        import dataclasses

        assert dataclasses.is_dataclass(operator_session)
        # frozen=True means setattr should raise.
        import pytest

        with pytest.raises(AttributeError):
            operator_session.human_id = "hacker"  # type: ignore[misc]

    def test_str_representation(self, operator_session: Session) -> None:
        text = str(operator_session)
        assert "alice" in text
        assert "operator" in text
