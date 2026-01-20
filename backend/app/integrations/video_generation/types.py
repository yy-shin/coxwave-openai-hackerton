"""Pydantic models for video generation inputs and outputs."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ImageInput(BaseModel):
    """Image input for video generation (first frame, last frame, or reference)."""

    url: Optional[str] = Field(None, description="URL to image file")
    base64: Optional[str] = Field(None, description="Base64-encoded image data")
    mime_type: Optional[Literal["image/jpeg", "image/png", "image/webp"]] = Field(
        None, description="Image MIME type (required when using base64)"
    )


class SoraInput(BaseModel):
    """Video generation input for Sora API."""

    provider: Literal["sora"] = "sora"
    model: Optional[Literal["sora-2", "sora-2-pro"]] = Field(
        None, description="Sora model identifier"
    )
    prompt: str = Field(..., max_length=4096, description="Text description for AI model")
    input_image: Optional[ImageInput] = Field(None, description="First frame / starting image")


class VeoInput(BaseModel):
    """Video generation input for Veo API."""

    provider: Literal["veo"] = "veo"
    model: Optional[
        Literal[
            # Gemini API (API key mode)
            "veo-3.1-generate-preview",
            # Vertex AI mode
            "veo-3.1-generate-001",
            "veo-3.1-fast-generate-001",
            "veo-3.1-fast-generate-preview",
        ]
    ] = Field(None, description="Veo model identifier")
    prompt: str = Field(..., max_length=4096, description="Text description for AI model")
    input_image: Optional[ImageInput] = Field(None, description="First frame / starting image")
    negative_prompt: Optional[str] = Field(None, description="What NOT to include")
    last_frame: Optional[ImageInput] = Field(None, description="Last frame for interpolation")
    reference_images: Optional[list[ImageInput]] = Field(
        None, max_length=3, description="Subject/character reference images (max 3)"
    )
    num_outputs: Optional[int] = Field(
        None, ge=1, le=4, description="Number of videos to generate (1-4)"
    )


# Union type for provider inputs
VideoGenerationInput = SoraInput | VeoInput


class GenerationConfig(BaseModel):
    """Configuration for video generation (applies to all providers)."""

    duration: int = Field(
        8,
        description="Video duration in seconds (4, 6, 8, 12). 6s: Veo only, 12s: Sora only",
    )
    aspect_ratio: Literal["16:9", "9:16"] = Field("9:16", description="Video aspect ratio (default: portrait)")
    resolution: Literal["720p"] = Field("720p", description="Video resolution (fixed at 720p)")


class GeneratedVideo(BaseModel):
    """Output from video generation."""

    id: str = Field(..., description="Provider's unique video identifier")
    status: Literal["queued", "in_progress", "completed", "failed"] = Field(
        ..., description="Generation status"
    )
    progress: Optional[int] = Field(
        None, ge=0, le=100, description="Generation progress percentage"
    )
    created_at: str = Field(..., description="ISO 8601 timestamp when generation started")
    video_url: Optional[str] = Field(None, description="Download URL (available when completed)")
    thumbnail_url: Optional[str] = Field(None, description="Thumbnail image URL")
    duration: Optional[int] = Field(None, description="Video length in seconds")
    resolution: Optional[str] = Field(None, description="Video resolution string")
    has_audio: Optional[bool] = Field(None, description="Whether video contains audio")
    selected: bool = Field(False, description="Whether user has selected this video for final assembly")
    error: Optional[str] = Field(None, description="Error message if failed")


class GenerationResult(BaseModel):
    """Result of a video generation request, including the input used."""

    input_index: int = Field(
        ..., ge=0, description="Index of the generation_input this result corresponds to"
    )
    provider: Literal["sora", "veo"] = Field(..., description="Video generation provider used")
    video: GeneratedVideo = Field(..., description="The generated video output")
