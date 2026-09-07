"""Provider-neutral deployment secret boundary."""
from __future__ import annotations

from abc import ABC, abstractmethod
import os


class SecretProvider(ABC):
    """Source of deployment-managed secrets; implementations must not log values."""

    @abstractmethod
    def get_required(self, name: str) -> str:
        """Return a non-empty secret or fail closed."""
        raise NotImplementedError


class EnvironmentSecretProvider(SecretProvider):
    """Deployment-compatible provider backed by environment variables."""

    def __init__(self, env: dict[str, str] | None = None) -> None:
        self._env = os.environ if env is None else env

    def get_required(self, name: str) -> str:
        value = self._env.get(name, "")
        if not value:
            raise RuntimeError(f"missing required deployment secret: {name}")
        return value


class MappingSecretProvider(SecretProvider):
    """Test adapter for deterministic secret-boundary tests."""

    def __init__(self, values: dict[str, str]) -> None:
        self._values = dict(values)

    def get_required(self, name: str) -> str:
        value = self._values.get(name, "")
        if not value:
            raise RuntimeError(f"missing required deployment secret: {name}")
        return value
