"""Veo (Google) video generation provider implementation."""

import os
from datetime import datetime, timezone
from typing import Any

from google import genai
from google.genai import types

from ..exceptions import (
    InvalidConfigurationError,
    ProviderAuthenticationError,
    VideoGenerationRequestError,
    VideoNotFoundError,
)
from ..types import GeneratedVideo, GenerationConfig, ImageInput, VeoInput
from .base import VideoProvider


class VeoProvider(VideoProvider):
    """Veo video generation provider using Google GenAI SDK."""

    provider_name = "veo"

    # Veo supports these durations
    SUPPORTED_DURATIONS = [4, 6, 8]

    # Hardcoded defaults per spec
    GENERATE_AUDIO = True
    PERSON_GENERATION = "allow_all"

    def __init__(self, api_key: str | None = None, project: str | None = None):
        """
        Initialize Veo provider.

        Args:
            api_key: Google API key. If not provided, uses GOOGLE_API_KEY env var.
            project: Google Cloud project ID for Vertex AI mode (preferred for Veo).
        """
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        self.project = project or os.environ.get("GOOGLE_CLOUD_PROJECT")

        if not self.api_key and not self.project:
            raise ProviderAuthenticationError(
                "veo",
                "GOOGLE_API_KEY or GOOGLE_CLOUD_PROJECT environment variable not set",
            )

        # Initialize the client - prefer Vertex AI for Veo when project is set
        if self.project:
            # Vertex AI mode (uses default credentials / ADC)
            self.client = genai.Client(vertexai=True, project=self.project, location="us-central1")
            self.is_vertex_ai = True
        else:
            # API key mode (Gemini API)
            self.client = genai.Client(api_key=self.api_key)
            self.is_vertex_ai = False

        # Store operation mapping (operation_name -> created_at)
        self._operations: dict[str, str] = {}

    def _validate_duration(self, duration: int) -> int:
        """Validate and return duration for Veo."""
        if duration not in self.SUPPORTED_DURATIONS:
            # Find closest supported duration
            closest = min(self.SUPPORTED_DURATIONS, key=lambda x: abs(x - duration))
            return closest
        return duration

    def _get_aspect_ratio(self, config: GenerationConfig) -> str:
        """Get aspect ratio string for Veo API."""
        return config.aspect_ratio

    def _build_image(self, image: ImageInput) -> types.Image:
        """Build Image object for Veo API.

        Note: Veo's types.Image only supports:
        - gcsUri: For Google Cloud Storage URIs (gs://...)
        - imageBytes + mimeType: For raw image bytes

        HTTP URLs must be downloaded first or converted to base64.
        """
        if image.url:
            # Check if it's a GCS URI
            if image.url.startswith("gs://"):
                return types.Image(gcsUri=image.url)
            # For HTTP URLs, the caller should have converted to base64
            # or we can try using from_file which handles more cases
            try:
                return types.Image.from_file(location=image.url)
            except Exception:
                raise InvalidConfigurationError(
                    "veo",
                    "HTTP URLs must be converted to base64 or use GCS URIs (gs://...)",
                )
        elif image.base64 and image.mime_type:
            # Convert base64 string to bytes
            import base64 as b64

            image_bytes = b64.b64decode(image.base64)
            return types.Image(
                imageBytes=image_bytes,
                mimeType=image.mime_type,
            )
        raise InvalidConfigurationError("veo", "Image must have url (GCS) or base64+mime_type")

    def _parse_operation_to_video(
        self,
        operation_name: str,
        response: Any = None,
        error: str | None = None,
    ) -> GeneratedVideo:
        """Convert operation response to GeneratedVideo."""
        created_at = self._operations.get(
            operation_name,
            datetime.now(tz=timezone.utc).isoformat(),
        )

        # Determine status based on operation state
        if error:
            return GeneratedVideo(
                id=operation_name,
                status="failed",
                created_at=created_at,
                error=error,
                has_audio=self.GENERATE_AUDIO,
            )

        if response is None:
            return GeneratedVideo(
                id=operation_name,
                status="in_progress",
                created_at=created_at,
                has_audio=self.GENERATE_AUDIO,
            )

        # Check if we have generated videos
        generated_videos = getattr(response, "generated_videos", None)
        if generated_videos and len(generated_videos) > 0:
            video = generated_videos[0]
            video_uri = getattr(video, "video", None)
            if video_uri:
                video_url = getattr(video_uri, "uri", None)
            else:
                video_url = None

            return GeneratedVideo(
                id=operation_name,
                status="completed",
                created_at=created_at,
                video_url=video_url,
                has_audio=self.GENERATE_AUDIO,
                resolution="720p",
            )

        # Still in progress
        return GeneratedVideo(
            id=operation_name,
            status="in_progress",
            created_at=created_at,
            has_audio=self.GENERATE_AUDIO,
        )

    async def generate(
        self,
        input_data: VeoInput,
        config: GenerationConfig,
    ) -> GeneratedVideo:
        """Start video generation with Veo."""
        duration = self._validate_duration(config.duration)
        aspect_ratio = self._get_aspect_ratio(config)

        # Build generation config
        model_name = input_data.model or "veo-3.1-generate-preview"

        # Build config kwargs - generate_audio and person_generation only work in Vertex AI
        config_kwargs = {
            "aspect_ratio": aspect_ratio,
            "duration_seconds": duration,
            "negative_prompt": input_data.negative_prompt,
            "number_of_videos": input_data.num_outputs or 1,
        }
        if self.is_vertex_ai:
            config_kwargs["generate_audio"] = self.GENERATE_AUDIO
            config_kwargs["person_generation"] = self.PERSON_GENERATION

        # Build the request
        generate_config = types.GenerateVideosConfig(**config_kwargs)

        # Build image inputs if provided
        image = None
        if input_data.input_image:
            image = self._build_image(input_data.input_image)

        # Build reference images if provided
        if input_data.reference_images:
            reference_images = [
                self._build_image(img) for img in input_data.reference_images
            ]
            config_kwargs["reference_images"] = reference_images
            generate_config = types.GenerateVideosConfig(**config_kwargs)

        try:
            # Start the generation operation
            operation = self.client.models.generate_videos(
                model=model_name,
                prompt=input_data.prompt,
                image=image,
                config=generate_config,
            )

            # Store operation metadata
            operation_name = getattr(operation, "name", str(id(operation)))
            created_at = datetime.now(tz=timezone.utc).isoformat()
            self._operations[operation_name] = created_at

            return GeneratedVideo(
                id=operation_name,
                status="in_progress",
                created_at=created_at,
                has_audio=self.GENERATE_AUDIO,
            )

        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg or "403" in error_msg or "authentication" in error_msg.lower():
                raise ProviderAuthenticationError("veo", error_msg)
            raise VideoGenerationRequestError("veo", details=error_msg)

    async def get_status(self, video_id: str) -> GeneratedVideo:
        """Get status of a Veo video generation (operation)."""
        try:
            # Get operation status
            operation = self.client.operations.get(name=video_id)

            # Check if operation is done
            if hasattr(operation, "done") and operation.done:
                # Check for error
                if hasattr(operation, "error") and operation.error:
                    return self._parse_operation_to_video(
                        video_id,
                        error=str(operation.error),
                    )

                # Get the result
                if hasattr(operation, "response"):
                    return self._parse_operation_to_video(video_id, operation.response)

            # Still in progress
            return self._parse_operation_to_video(video_id)

        except Exception as e:
            error_msg = str(e)
            if "404" in error_msg or "not found" in error_msg.lower():
                raise VideoNotFoundError("veo", video_id)
            if "401" in error_msg or "403" in error_msg:
                raise ProviderAuthenticationError("veo", error_msg)
            raise VideoGenerationRequestError("veo", details=error_msg)

    async def get_video_url(self, video_id: str) -> str:
        """Get download URL for a completed Veo video."""
        status = await self.get_status(video_id)
        if status.status != "completed":
            raise VideoGenerationRequestError(
                "veo",
                details=f"Video is not completed (status: {status.status})",
            )
        if not status.video_url:
            raise VideoGenerationRequestError(
                "veo",
                details="Video URL not available",
            )
        return status.video_url

    async def generate_multiple(
        self,
        input_data: VeoInput,
        config: GenerationConfig,
    ) -> list[GeneratedVideo]:
        """
        Generate multiple videos from a single input (using num_outputs).

        This is a convenience method that returns all generated videos from
        a single operation.
        """
        duration = self._validate_duration(config.duration)
        aspect_ratio = self._get_aspect_ratio(config)
        model_name = input_data.model or "veo-3.1-generate-preview"
        num_outputs = input_data.num_outputs or 1

        # Build config kwargs - generate_audio and person_generation only work in Vertex AI
        config_kwargs = {
            "aspect_ratio": aspect_ratio,
            "duration_seconds": duration,
            "negative_prompt": input_data.negative_prompt,
            "number_of_videos": num_outputs,
        }
        if self.is_vertex_ai:
            config_kwargs["generate_audio"] = self.GENERATE_AUDIO
            config_kwargs["person_generation"] = self.PERSON_GENERATION

        generate_config = types.GenerateVideosConfig(**config_kwargs)

        image = None
        if input_data.input_image:
            image = self._build_image(input_data.input_image)

        if input_data.reference_images:
            reference_images = [
                self._build_image(img) for img in input_data.reference_images
            ]
            config_kwargs["reference_images"] = reference_images
            generate_config = types.GenerateVideosConfig(**config_kwargs)

        try:
            operation = self.client.models.generate_videos(
                model=model_name,
                prompt=input_data.prompt,
                image=image,
                config=generate_config,
            )

            # Wait for the result
            result = operation.result()

            # Parse all generated videos
            created_at = datetime.now(tz=timezone.utc).isoformat()
            videos = []

            if hasattr(result, "generated_videos"):
                for i, gen_video in enumerate(result.generated_videos):
                    video_uri = getattr(gen_video, "video", None)
                    video_url = getattr(video_uri, "uri", None) if video_uri else None

                    videos.append(
                        GeneratedVideo(
                            id=f"{operation.name}_{i}",
                            status="completed",
                            created_at=created_at,
                            video_url=video_url,
                            has_audio=self.GENERATE_AUDIO,
                            resolution="720p",
                        )
                    )

            return videos

        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg or "403" in error_msg:
                raise ProviderAuthenticationError("veo", error_msg)
            raise VideoGenerationRequestError("veo", details=error_msg)
