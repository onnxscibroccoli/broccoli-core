"""Provider-agnostic rotation of authorized account sessions.

Scheduling state only. Credentials, OAuth tokens, and provider-specific
authentication remain outside the repository.
"""

from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from typing import Iterable


@dataclass
class Account:
    account_id: str
    provider: str
    available: bool = True
    cooldown_until: float = 0.0

    def usable(self, now: float | None = None) -> bool:
        now = monotonic() if now is None else now
        return self.available and now >= self.cooldown_until


class AccountPool:
    """Fair round-robin scheduler across configured account/provider pairs."""

    def __init__(self, accounts: Iterable[Account] = ()) -> None:
        self._accounts = list(accounts)
        self._cursor = 0

    @property
    def accounts(self) -> tuple[Account, ...]:
        return tuple(self._accounts)

    def add(self, account: Account) -> None:
        if any(a.account_id == account.account_id for a in self._accounts):
            raise ValueError(f"Duplicate account_id: {account.account_id!r}")
        self._accounts.append(account)

    def select(
        self,
        now: float | None = None,
        preferred_provider: str | None = None,
    ) -> Account | None:
        """Return the next usable account, optionally preferring a provider.

        Provider preference changes selection priority without consuming the
        normal round-robin position. Normal selection advances past the
        account actually selected, including when earlier accounts are
        unavailable or cooling down.
        """
        if not self._accounts:
            return None

        now = monotonic() if now is None else now
        count = len(self._accounts)
        start_index = self._cursor

        offsets = list(range(count))
        preferred_offsets: set[int] = set()

        if preferred_provider is not None:
            preferred_offsets = {
                offset
                for offset in offsets
                if self._accounts[
                    (start_index + offset) % count
                ].provider == preferred_provider
            }

            preferred = [
                offset
                for offset in offsets
                if offset in preferred_offsets
            ]
            remaining = [
                offset for offset in offsets
                if offset not in preferred_offsets
            ]
            offsets = preferred + remaining

        for offset in offsets:
            index = (start_index + offset) % count
            account = self._accounts[index]

            if account.usable(now):
                if (
                    preferred_provider is not None
                    and offset in preferred_offsets
                ):
                    # Provider preference is opportunistic. Do not consume
                    # the normal round-robin position.
                    self._cursor = start_index
                else:
                    # Normal selection advances past the actual account
                    # selected, not merely past the original cursor.
                    self._cursor = (index + 1) % count

                return account

        return None

    def mark_unavailable(self, account_id: str) -> None:
        self._get(account_id).available = False

    def mark_available(self, account_id: str) -> None:
        account = self._get(account_id)
        account.available = True
        account.cooldown_until = 0.0

    def cooldown(
        self,
        account_id: str,
        seconds: float,
        now: float | None = None,
    ) -> None:
        if seconds < 0:
            raise ValueError("seconds must be non-negative")

        now = monotonic() if now is None else now
        self._get(account_id).cooldown_until = now + seconds

    def _get(self, account_id: str) -> Account:
        for account in self._accounts:
            if account.account_id == account_id:
                return account

        raise KeyError(account_id)
