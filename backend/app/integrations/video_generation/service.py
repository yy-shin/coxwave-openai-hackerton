"""Unified video generation service that routes to appropriate providers."""

import asyncio
from typing import Literal

from .exceptions import ProviderNotFoundError
from .providers import SoraProvider, VeoProvider, VideoProvider
from .types import (
    GeneratedVideo,
    GenerationConfig,
    GenerationResult,
    SoraInput,
    VeoInput,
    VideoGenerationInput,
)


class VideoGenerationService:
    """
    Unified service for video generation across multiple providers.

    Routes requests to the appropriate provider (Sora or Veo) based on
    the input's provider field.
    """

    def __init__(
        self,
        sora_api_key: str | None = None,
        google_api_key: str | None = None,
        google_project: str | None = None,
    ):
        """
        Initialize the video generation service.

        Args:
            sora_api_key: OpenAI API key for Sora. Uses OPENAI_API_KEY env var if not provided.
            google_api_key: Google API key for Veo. Uses GOOGLE_API_KEY env var if not provided.
            google_project: Google Cloud project for Vertex AI mode.
        """
        self._providers: dict[str, VideoProvider] = {}
        self._sora_api_key = sora_api_key
        self._google_api_key = google_api_key
        self._google_project = google_project

    def _get_provider(self, provider_name: Literal["sora", "veo"]) -> VideoProvider:
        """Get or create a provider instance."""
        if provider_name not in self._providers:
            if provider_name == "sora":
                self._providers["sora"] = SoraProvider(api_key=self._sora_api_key)
            elif provider_name == "veo":
                self._providers["veo"] = VeoProvider(
                    api_key=self._google_api_key,
                    project=self._google_project,
                )
            else:
                raise ProviderNotFoundError(provider_name)
        return self._providers[provider_name]

    async def generate(
        self,
        input_data: VideoGenerationInput,
        config: GenerationConfig | None = None,
    ) -> GeneratedVideo:
        """
        Generate a video using the appropriate provider.

        Args:
            input_data: SoraInput or VeoInput with provider field
            config: Generation configuration. Uses defaults if not provided.

        Returns:
            GeneratedVideo with initial status

        Example:
            service = VideoGenerationService()
            result = await service.generate(
                SoraInput(prompt="A cat walking"),
                GenerationConfig(duration=8, aspect_ratio="16:9")
            )
        """
        if config is None:
            config = GenerationConfig()

        provider = self._get_provider(input_data.provider)
        return await provider.generate(input_data, config)

    async def generate_batch(
        self,
        inputs: list[tuple[VideoGenerationInput, int]],
        config: GenerationConfig | None = None,
    ) -> list[GenerationResult]:
        """
        Generate multiple videos in parallel.

        Args:
            inputs: List of (input_data, input_index) tuples
            config: Generation configuration applied to all inputs

        Returns:
            List of GenerationResult objects with input_index preserved

        Example:
            results = await service.generate_batch([
                (SoraInput(prompt="Cat walking"), 0),
                (VeoInput(prompt="Dog running"), 1),
            ], GenerationConfig(duration=8))
        """
        if config is None:
            config = GenerationConfig()

        async def generate_one(
            input_data: VideoGenerationInput, input_index: int
        ) -> GenerationResult:
            video = await self.generate(input_data, config)
            return GenerationResult(
                input_index=input_index,
                provider=input_data.provider,
                video=video,
            )

        tasks = [generate_one(input_data, idx) for input_data, idx in inputs]
        return await asyncio.gather(*tasks)

    async def get_status(
        self,
        provider: Literal["sora", "veo"],
        video_id: str,
    ) -> GeneratedVideo:
        """
        Get the current status of a video generation.

        Args:
            provider: The provider that created the video ("sora" or "veo")
            video_id: The provider's unique video identifier

        Returns:
            GeneratedVideo with current status and progress
        """
        provider_instance = self._get_provider(provider)
        return await provider_instance.get_status(video_id)

    async def wait_for_completion(
        self,
        provider: Literal["sora", "veo"],
        video_id: str,
        poll_interval: float = 5.0,
        timeout: float = 600.0,
    ) -> GeneratedVideo:
        """
        Wait for a video generation to complete.

        Args:
            provider: The provider that created the video ("sora" or "veo")
            video_id: The provider's unique video identifier
            poll_interval: Seconds between status checks
            timeout: Maximum seconds to wait

        Returns:
            GeneratedVideo with final status (completed or failed)
        """
        provider_instance = self._get_provider(provider)
        return await provider_instance.wait_for_completion(
            video_id, poll_interval, timeout
        )

    async def wait_for_batch(
        self,
        videos: list[tuple[Literal["sora", "veo"], str, int]],
        poll_interval: float = 5.0,
        timeout: float = 600.0,
    ) -> list[GenerationResult]:
        """
        Wait for multiple video generations to complete in parallel.

        Args:
            videos: List of (provider, video_id, input_index) tuples
            poll_interval: Seconds between status checks
            timeout: Maximum seconds to wait

        Returns:
            List of GenerationResult objects with final statuses
        """

        async def wait_one(
            provider: Literal["sora", "veo"], video_id: str, input_index: int
        ) -> GenerationResult:
            video = await self.wait_for_completion(
                provider, video_id, poll_interval, timeout
            )
            return GenerationResult(
                input_index=input_index,
                provider=provider,
                video=video,
            )

        tasks = [wait_one(provider, video_id, idx) for provider, video_id, idx in videos]
        return await asyncio.gather(*tasks)

    async def get_video_url(
        self,
        provider: Literal["sora", "veo"],
        video_id: str,
    ) -> str:
        """
        Get the download URL for a completed video.

        Args:
            provider: The provider that created the video
            video_id: The provider's unique video identifier

        Returns:
            URL string for downloading the video
        """
        provider_instance = self._get_provider(provider)
        return await provider_instance.get_video_url(video_id)
