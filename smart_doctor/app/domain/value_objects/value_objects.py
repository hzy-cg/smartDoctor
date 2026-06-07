from dataclasses import dataclass


@dataclass(frozen=True)
class Symptom:
    name: str
    location: str | None = None
    duration: str | None = None
    severity: int | None = None
    description: str | None = None


@dataclass(frozen=True)
class Department:
    name: str
    category: str | None = None
    keywords: list[str] | None = None
    description: str | None = None


@dataclass(frozen=True)
class VoiceConfig:
    voice_style: str = "default"
    speech_rate: float = 1.0
    pitch: float = 1.0
