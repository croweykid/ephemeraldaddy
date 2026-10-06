from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time


@dataclass(frozen=True)
class BatchImportSeed:
    name: str
    alias: str = ""
    from_whence: str = ""
    tags: tuple[str, ...] = ()
    notes: str = ""
    birth_date: str = ""
    birth_time: str = ""
    birth_place: str = ""
    biography: str = ""
    sources: tuple[str, ...] = ()
    data_rating: str = ""
    restored: bool = False

    def to_row(self) -> BatchImportRow:
        return BatchImportRow(
            requested_name=self.name, name=self.name,
            alias=self.alias, from_whence=self.from_whence,
            tags=list(self.tags), notes=self.notes,
            birth_date=self.birth_date, birth_time=self.birth_time,
            birth_place=self.birth_place, biography=self.biography,
            sources=list(self.sources), data_rating=self.data_rating,
        )


@dataclass(frozen=True)
class ValidatedPlace:
    label: str
    latitude: float
    longitude: float


@dataclass
class BatchImportRow:
    requested_name: str
    name: str = ""
    birth_date: str = ""
    birth_time: str = ""
    birth_place: str = ""
    biography: str = ""
    sources: list[str] = field(default_factory=list)
    alias: str = ""
    from_whence: str = ""
    tags: list[str] = field(default_factory=list)
    notes: str = ""
    data_rating: str = ""
    place: ValidatedPlace | None = None
    blocking_errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    included: bool = False

    def clear_place_errors(self) -> None:
        self.blocking_errors[:] = [
            error for error in self.blocking_errors
            if not error.startswith("Birth place could not be resolved:")
        ]

    def set_birth_place(self, value: str) -> None:
        value = value.strip()
        if value != self.birth_place:
            self.clear_place_errors()
            self.place = None
            self.included = False
        self.birth_place = value

    def validation_errors(self) -> list[str]:
        errors: list[str] = []
        if not self.name.strip(): errors.append("Name is blank.")
        try: date.fromisoformat(self.birth_date)
        except ValueError: errors.append("Birth date is invalid.")
        if self.birth_time.strip() and self.birth_time.strip().lower() != "unknown":
            try: time.fromisoformat(self.birth_time)
            except ValueError: errors.append("Birth time is invalid.")
        if not self.birth_place.strip(): errors.append("Birth place is blank.")
        elif self.place is None: errors.append("Birth place has not been validated.")
        return list(dict.fromkeys([*self.blocking_errors, *errors]))

    @property
    def importable(self) -> bool:
        return not self.validation_errors()

    @property
    def error_text(self) -> str:
        return " ".join([*self.validation_errors(), *self.warnings])
