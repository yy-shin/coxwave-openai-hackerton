"""Sora (OpenAI) video generation provider implementation."""

import base64
import os
from datetime import datetime, timezone
from typing import Any

import httpx

from ..exceptions import (
    InvalidConfigurationError,
    ProviderAuthenticationError,
    VideoGenerationRequestError,
    VideoNotFoundError,
)
from ..types import GeneratedVideo, GenerationConfig, ImageInput, SoraInput
from .base import VideoProvider


class SoraProvider(VideoProvider):
    """Sora video generation provider using OpenAI API."""

    provider_name = "sora"
    BASE_URL = "https://api.openai.com/v1"

    # Map aspect_ratio + resolution to size string for Sora
    SIZE_MAP = {
        ("16:9", "720p"): "1280x720",
        ("9:16", "720p"): "720x1280",
    }

    # Sora supports these durations
    SUPPORTED_DURATIONS = [4, 8, 12]

    def __init__(self, api_key: str | None = None):
        """
        Initialize Sora provider.

        Args:
            api_key: OpenAI API key. If not provided, uses OPENAI_API_KEY env var.
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ProviderAuthenticationError(
                "sora", "OPENAI_API_KEY environment variable not set"
            )

    def _get_headers(self, content_type: str = "application/json") -> dict[str, str]:
        """Get HTTP headers for API requests."""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def _get_size(self, config: GenerationConfig) -> str:
        """Convert aspect_ratio and resolution to Sora size string."""
        key = (config.aspect_ratio, config.resolution)
        if key not in self.SIZE_MAP:
            raise InvalidConfigurationError(
                "sora",
                f"Unsupported aspect_ratio/resolution combination: {config.aspect_ratio}/{config.resolution}",
            )
        return self.SIZE_MAP[key]

    def _validate_duration(self, duration: int) -> int:
        """Validate and return duration for Sora."""
        if duration not in self.SUPPORTED_DURATIONS:
            # Find closest supported duration
            closest = min(self.SUPPORTED_DURATIONS, key=lambda x: abs(x - duration))
            return closest
        return duration

    def _build_image_input(self, image: ImageInput) -> dict[str, Any]:
        """Build image input for Sora API."""
        if image.url:
            return {"type": "url", "url": image.url}
        elif image.base64 and image.mime_type:
            return {
                "type": "base64",
                "base64": image.base64,
                "media_type": image.mime_type,
            }
        raise InvalidConfigurationError("sora", "Image must have url or base64+mime_type")

    def _parse_video_response(self, data: dict[str, Any]) -> GeneratedVideo:
        """Parse Sora API response to GeneratedVideo."""
        # Convert Unix timestamp to ISO format
        created_at = data.get("created_at")
        if isinstance(created_at, int):
            created_at = datetime.fromtimestamp(created_at, tz=timezone.utc).isoformat()
        elif not created_at:
            created_at = datetime.now(tz=timezone.utc).isoformat()

        # Build video URL if completed
        video_url = None
        if data.get("status") == "completed":
            video_id = data.get("id", "")
            video_url = f"{self.BASE_URL}/videos/{video_id}/content"

        return GeneratedVideo(
            id=data.get("id", ""),
            status=data.get("status", "queued"),
            progress=data.get("progress"),
            created_at=created_at,
            video_url=video_url,
            duration=data.get("seconds"),
            resolution=data.get("size"),
            has_audio=False,  # Sora doesn't generate audio
            error=data.get("failure_reason") or data.get("error"),
        )

    async def generate(
        self,
        input_data: SoraInput,
        config: GenerationConfig,
    ) -> GeneratedVideo:
        """Start video generation with Sora."""
        size = self._get_size(config)
        duration = self._validate_duration(config.duration)

        async with httpx.AsyncClient() as client:
            # Check if we have an input image - use multipart form data
            if input_data.input_image:
                # Build multipart form data
                form_data = {
                    "model": input_data.model or "sora-2",
                    "prompt": input_data.prompt,
                    "size": size,
                    "seconds": str(duration),
                }

                # Prepare the image file
                image = input_data.input_image
                if image.base64 and image.mime_type:
                    # Decode base64 to bytes
                    image_bytes = base64.b64decode(image.base64)
                    # Determine file extension from mime type
                    ext = image.mime_type.split("/")[-1]
                    if ext == "jpeg":
                        ext = "jpg"
                    filename = f"input_image.{ext}"

                    files = {
                        "input_reference": (filename, image_bytes, image.mime_type),
                    }

                    response = await client.post(
                        f"{self.BASE_URL}/videos",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        data=form_data,
                        files=files,
                        timeout=60.0,
                    )
                elif image.url:
                    # For URL, we need to download and re-upload
                    # Or use JSON format if API supports it
                    # For now, download the image first
                    img_response = await client.get(image.url, timeout=30.0)
                    img_response.raise_for_status()
                    image_bytes = img_response.content

                    # Guess content type
                    content_type = img_response.headers.get("content-type", "image/jpeg")
                    ext = content_type.split("/")[-1]
                    if ext == "jpeg":
                        ext = "jpg"
                    filename = f"input_image.{ext}"

                    files = {
                        "input_reference": (filename, image_bytes, content_type),
                    }

                    response = await client.post(
                        f"{self.BASE_URL}/videos",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        data=form_data,
                        files=files,
                        timeout=60.0,
                    )
                else:
                    raise InvalidConfigurationError(
                        "sora", "Image must have url or base64+mime_type"
                    )
            else:
                # No image - use JSON payload
                payload: dict[str, Any] = {
                    "model": input_data.model or "sora-2",
                    "prompt": input_data.prompt,
                    "size": size,
                    "seconds": duration,
                }

                response = await client.post(
                    f"{self.BASE_URL}/videos",
                    headers=self._get_headers(),
                    json=payload,
                    timeout=30.0,
                )

            if response.status_code == 401:
                raise ProviderAuthenticationError("sora", "Invalid API key")

            if response.status_code != 200 and response.status_code != 201:
                error_detail = None
                try:
                    error_data = response.json()
                    error_detail = error_data.get("error", {}).get("message")
                except Exception:
                    error_detail = response.text
                raise VideoGenerationRequestError(
                    "sora", response.status_code, error_detail
                )

            data = response.json()
            return self._parse_video_response(data)

    async def get_status(self, video_id: str) -> GeneratedVideo:
        """Get status of a Sora video generation."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/videos/{video_id}",
                headers=self._get_headers(),
                timeout=30.0,
            )

            if response.status_code == 404:
                raise VideoNotFoundError("sora", video_id)

            if response.status_code == 401:
                raise ProviderAuthenticationError("sora", "Invalid API key")

            if response.status_code != 200:
                error_detail = None
                try:
                    error_data = response.json()
                    error_detail = error_data.get("error", {}).get("message")
                except Exception:
                    error_detail = response.text
                raise VideoGenerationRequestError(
                    "sora", response.status_code, error_detail
                )

            data = response.json()
            return self._parse_video_response(data)

    async def get_video_url(self, video_id: str) -> str:
        """Get download URL for a completed Sora video."""
        status = await self.get_status(video_id)
        if status.status != "completed":
            raise VideoGenerationRequestError(
                "sora",
                details=f"Video is not completed (status: {status.status})",
            )
        return f"{self.BASE_URL}/videos/{video_id}/content"
