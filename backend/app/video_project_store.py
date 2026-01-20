"""Domain-specific store for video project state, keyed by thread ID."""

from __future__ import annotations

import asyncio
from typing import Callable, Dict

from .video_project_state import VideoProjectState


class VideoProjectStore:
    """Thread-safe in-memory store for video project state."""

    def __init__(self) -> None:
        self._states: Dict[str, VideoProjectState] = {}
        self._lock = asyncio.Lock()

    def _ensure(self, thread_id: str) -> VideoProjectState:
        """Ensure a state exists for the given thread ID."""
        state = self._states.get(thread_id)
        if state is None:
            state = VideoProjectState()
            self._states[thread_id] = state
        return state

    async def load(self, thread_id: str) -> VideoProjectState:
        """Load the state for a thread, returning a clone."""
        async with self._lock:
            return self._ensure(thread_id).clone()

    async def mutate(
        self, thread_id: str, mutator: Callable[[VideoProjectState], None]
    ) -> VideoProjectState:
        """Apply a mutation to the state and return a clone."""
        async with self._lock:
            state = self._ensure(thread_id)
            mutator(state)
            return state.clone()
