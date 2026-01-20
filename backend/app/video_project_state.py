"""Video project state model for tracking video generation workflows."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ImageInput(BaseModel):
    """An image input with local file path."""

    file_path: str = Field(description="Local file path to the image")


class GenerationInput(BaseModel):
    """Input configuration for a video generation provider."""

    provider: Literal["veo", "sora"]
    prompt: str
    negative_prompt: str | None = None
    reference_images: list[ImageInput] | None = None
    input_image: ImageInput | None = None


class Segment(BaseModel):
    """A single segment/scene in the storyboard."""

    scene_description: str
    duration: float
    generation_inputs: list[GenerationInput]
    # Output fields (populated after generation)
    selected_video_url: str | None = None
    video_variants: list[str] = Field(default_factory=list)
    selected_variant_index: int | None = None


class Storyboard(BaseModel):
    """Storyboard containing all segments."""

    segments: list[Segment] = Field(default_factory=list)


class VideoProjectState(BaseModel):
    """State for a video generation project."""

    title: str = "Untitled Project"
    description: str = ""
    aspect_ratio: str = "16:9"
    total_duration: int = 30

    # Input specifications
    reference_video_url: str | None = None
    reference_images: list[ImageInput] = Field(default_factory=list)

    # Storyboard
    storyboard: Storyboard = Field(default_factory=Storyboard)
    storyboard_approved: bool = False

    # Outputs
    final_video_url: str | None = None
    thumbnail_url: str | None = None
    banner_url: str | None = None
    marketing_copy: str | None = None

    # Metadata
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now(UTC)

    def set_storyboard(self, segments: list[Segment]) -> None:
        """Set the storyboard segments."""
        self.storyboard = Storyboard(segments=segments)
        self.touch()

    def approve_storyboard(self) -> None:
        """Mark storyboard as approved."""
        self.storyboard_approved = True
        self.touch()

    def select_variant(self, segment_index: int, variant_index: int) -> None:
        """Select a video variant for a segment by index."""
        if 0 <= segment_index < len(self.storyboard.segments):
            seg = self.storyboard.segments[segment_index]
            seg.selected_variant_index = variant_index
            if seg.video_variants and 0 <= variant_index < len(seg.video_variants):
                seg.selected_video_url = seg.video_variants[variant_index]
        self.touch()

    def update_segment(self, segment_index: int, segment: Segment) -> bool:
        """Update a single segment in the storyboard by index.

        Returns True if the segment was updated, False if index is out of range.
        """
        if 0 <= segment_index < len(self.storyboard.segments):
            self.storyboard.segments[segment_index] = segment
            self.touch()
            return True
        return False

    def set_final_output(
        self,
        video_url: str,
        thumbnail_url: str,
        banner_url: str,
        marketing_copy: str,
    ) -> None:
        """Set the final output URLs and marketing copy."""
        self.final_video_url = video_url
        self.thumbnail_url = thumbnail_url
        self.banner_url = banner_url
        self.marketing_copy = marketing_copy
        self.touch()

    def clone(self) -> VideoProjectState:
        """Create a copy of this state."""
        return self.model_copy(deep=True)

    def to_payload(self, thread_id: str | None = None) -> dict[str, Any]:
        """Convert state to JSON-serializable payload for frontend."""
        payload: dict[str, Any] = self.model_dump(mode="json")
        # Convert snake_case to camelCase for frontend
        payload = {
            "title": self.title,
            "description": self.description,
            "aspectRatio": self.aspect_ratio,
            "totalDuration": self.total_duration,
            "referenceVideoUrl": self.reference_video_url,
            "referenceImages": [{"filePath": img.file_path} for img in self.reference_images],
            "storyboard": {
                "segments": [
                    {
                        "sceneDescription": seg.scene_description,
                        "duration": seg.duration,
                        "generationInputs": [
                            {
                                "provider": gi.provider,
                                "prompt": gi.prompt,
                                "negativePrompt": gi.negative_prompt,
                                "referenceImages": (
                                    [{"filePath": img.file_path} for img in gi.reference_images]
                                    if gi.reference_images
                                    else None
                                ),
                                "inputImage": (
                                    {"filePath": gi.input_image.file_path}
                                    if gi.input_image
                                    else None
                                ),
                            }
                            for gi in seg.generation_inputs
                        ],
                        "selectedVideoUrl": seg.selected_video_url,
                        "videoVariants": seg.video_variants,
                        "selectedVariantIndex": seg.selected_variant_index,
                    }
                    for seg in self.storyboard.segments
                ]
            },
            "storyboardApproved": self.storyboard_approved,
            "finalVideoUrl": self.final_video_url,
            "thumbnailUrl": self.thumbnail_url,
            "bannerUrl": self.banner_url,
            "marketingCopy": self.marketing_copy,
            "updatedAt": self.updated_at.isoformat(),
        }
        if thread_id:
            payload["threadId"] = thread_id
        return payload
