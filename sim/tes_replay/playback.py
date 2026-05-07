"""Time-controlled replay playback primitives for persisted TES runs."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

PlaybackState = Literal["playing", "paused"]


@dataclass(frozen=True)
class ReplayCursor:
    """Current replay playback position and speed."""

    step: int
    state: PlaybackState = "paused"
    speed: float = 1.0

    def __post_init__(self) -> None:
        if isinstance(self.step, bool) or self.step < 0:
            raise ValueError("step must be a non-negative integer")
        if self.state not in {"playing", "paused"}:
            raise ValueError("state must be playing or paused")
        if self.speed <= 0:
            raise ValueError("speed must be positive")


@dataclass(frozen=True)
class ReplayTimeline:
    """Sorted replay steps available for a run."""

    steps: tuple[int, ...]

    def __post_init__(self) -> None:
        if any(isinstance(step, bool) or step < 0 for step in self.steps):
            raise ValueError("timeline steps must be non-negative integers")
        if tuple(sorted(set(self.steps))) != self.steps:
            raise ValueError("timeline steps must be unique and sorted")

    @property
    def first_step(self) -> int:
        return self.steps[0] if self.steps else 0

    @property
    def last_step(self) -> int:
        return self.steps[-1] if self.steps else 0

    def clamp(self, step: int) -> int:
        if not self.steps:
            return 0
        return min(max(step, self.first_step), self.last_step)

    def next_step(self, step: int) -> int:
        for candidate in self.steps:
            if candidate > step:
                return candidate
        return self.last_step

    def previous_step(self, step: int) -> int:
        previous = self.first_step
        for candidate in self.steps:
            if candidate >= step:
                return previous
            previous = candidate
        return previous


@dataclass(frozen=True)
class ReplayPlaybackController:
    """Pure controller for replay play, pause, seek, and frame navigation."""

    timeline: ReplayTimeline
    cursor: ReplayCursor

    @classmethod
    def create(cls, timeline: ReplayTimeline, *, speed: float = 1.0) -> "ReplayPlaybackController":
        return cls(timeline=timeline, cursor=ReplayCursor(step=timeline.first_step, speed=speed))

    def play(self) -> "ReplayPlaybackController":
        return replace(self, cursor=replace(self.cursor, state="playing"))

    def pause(self) -> "ReplayPlaybackController":
        return replace(self, cursor=replace(self.cursor, state="paused"))

    def seek(self, step: int) -> "ReplayPlaybackController":
        return replace(self, cursor=replace(self.cursor, step=self.timeline.clamp(step)))

    def jump_to_step(self, step: int) -> "ReplayPlaybackController":
        return self.seek(step)

    def jump_to_event(self, event_step: int) -> "ReplayPlaybackController":
        return self.seek(event_step)

    def set_speed(self, speed: float) -> "ReplayPlaybackController":
        return replace(self, cursor=replace(self.cursor, speed=speed))

    def next_frame(self) -> "ReplayPlaybackController":
        return self.seek(self.timeline.next_step(self.cursor.step))

    def previous_frame(self) -> "ReplayPlaybackController":
        return self.seek(self.timeline.previous_step(self.cursor.step))
