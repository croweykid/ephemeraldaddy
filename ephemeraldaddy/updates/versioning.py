"""Small, dependency-free release-version primitives."""

from __future__ import annotations

import re
from dataclasses import dataclass

_VERSION_PATTERN = re.compile(
    r"^(?P<major>0|[1-9]\d*)\."
    r"(?P<minor>0|[1-9]\d*)\."
    r"(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>[0-9A-Za-z.-]+))?$"
)


@dataclass(frozen=True, slots=True)
class ReleaseVersion:
    """A comparable SemVer-style application release version."""

    major: int
    minor: int
    patch: int
    prerelease: tuple[str, ...] = ()

    @classmethod
    def parse(cls, value: str) -> "ReleaseVersion":
        match = _VERSION_PATTERN.fullmatch(str(value).strip())
        if match is None:
            raise ValueError(f"Invalid release version: {value!r}")
        prerelease = tuple(filter(None, (match.group("prerelease") or "").split(".")))
        return cls(
            int(match.group("major")),
            int(match.group("minor")),
            int(match.group("patch")),
            prerelease,
        )

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        return f"{base}-{'.'.join(self.prerelease)}" if self.prerelease else base

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, ReleaseVersion):
            return NotImplemented
        core = (self.major, self.minor, self.patch)
        other_core = (other.major, other.minor, other.patch)
        if core != other_core:
            return core < other_core
        if not self.prerelease:
            return False
        if not other.prerelease:
            return True
        return self._prerelease_key() < other._prerelease_key()

    def _prerelease_key(self) -> tuple[tuple[int, object], ...]:
        return tuple(
            (0, int(part)) if part.isdigit() else (1, part.lower())
            for part in self.prerelease
        )
