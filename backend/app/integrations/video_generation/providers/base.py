"""Abstract base class for video generation providers."""

import asyncio
from abc import ABC, abstractmethod
from typing import TypeVar

from ..exceptions import VideoGenerationTimeoutError
from ..types import GeneratedVideo, GenerationConfig, VideoGenerationInput

T = TypeVar("T", bound=VideoGenerationInput)


class VideoProvider(ABC):
    """Abstract base class for video generation providers."""

    provider_name: str = "base"

    @abstractmethod
    async def generate(
        self,
        input_data: VideoGenerationInput,
        config: GenerationConfig,
    ) -> GeneratedVideo:
        """
        Start video generation and return initial status.

        Args:
            input_data: Provider-specific input data (SoraInput or VeoInput)
            config: Generation configuration (duration, aspect_ratio, resolution)

        Returns:
            GeneratedVideo with initial status (usually 'queued' or 'in_progress')
        """
        ...

    @abstractmethod
    async def get_status(self, video_id: str) -> GeneratedVideo:
        """
        Get the current status of a video generation.

        Args:
            video_id: The provider's unique video identifier

        Returns:
            GeneratedVideo with current status and progress
        """
        ...

    @abstractmethod
    async def get_video_url(self, video_id: str) -> str:
        """
        Get the download URL for a completed video.

        Args:
            video_id: The provider's unique video identifier

        Returns:
            URL string for downloading the video

        Raises:
            VideoNotFoundError: If video doesn't exist
            VideoGenerationError: If video is not completed
        """
        ...

    async def wait_for_completion(
        self,
        video_id: str,
        poll_interval: float = 5.0,
        timeout: float = 600.0,
    ) -> GeneratedVideo:
        """
        Wait for video generation to complete, polling periodically.

        Args:
            video_id: The provider's unique video identifier
            poll_interval: Seconds between status checks (default: 5.0)
            timeout: Maximum seconds to wait (default: 600.0 = 10 minutes)

        Returns:
            GeneratedVideo with final status (completed or failed)

        Raises:
            VideoGenerationTimeoutError: If timeout is reached
        """
        elapsed = 0.0

        while elapsed < timeout:
            status = await self.get_status(video_id)

            if status.status in ("completed", "failed"):
                return status

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        raise VideoGenerationTimeoutError(
            provider=self.provider_name,
            video_id=video_id,
            timeout_seconds=timeout,
        )
