"""Provider-neutral deployment secret boundary."""
from __future__ import annotations

from abc import ABC, abstractmethod
import os


class SecretProvider(ABC):
    """Source of deployment-managed secrets; implementations must not log values."""

    @abstractmethod
    def get_required(self, name: str) -> str:
        """Return a non-empty, non-whitespace secret or fail closed."""
        raise NotImplementedError


def _validated_secret(name: str, value: str | None) -> str:
    # Do not trim a secret: whitespace may be part of a legitimate secret.
    # Reject values that are empty or entirely whitespace, and never echo values.
    if value is None or not value.strip():
        raise RuntimeError(f"missing required deployment secret: {name}")
    return value


class EnvironmentSecretProvider(SecretProvider):
    """Deployment-compatible provider backed by environment variables."""

    def __init__(self, env: dict[str, str] | None = None) -> None:
        self._env = os.environ if env is None else env

    def get_required(self, name: str) -> str:
        return _validated_secret(name, self._env.get(name))


class MappingSecretProvider(SecretProvider):
    """Test adapter for deterministic secret-boundary tests."""

    def __init__(self, values: dict[str, str]) -> None:
        self._values = dict(values)

    def get_required(self, name: str) -> str:
        return _validated_secret(name, self._values.get(name))
