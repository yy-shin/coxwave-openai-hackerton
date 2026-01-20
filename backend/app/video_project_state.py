"""Video project state model for tracking video generation workflows."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import Enum
from typing import Any, List, Optional


class ProjectPhase(str, Enum):
    """Current phase of the video generation workflow."""

    CLARIFYING = "clarifying"  # Asking clarifying questions
    STORYBOARD = "storyboard"  # Creating/reviewing storyboard
    GENERATING = "generating"  # Video generation in progress
    SELECTION = "selection"  # User selecting video variants
    ASSEMBLING = "assembling"  # Final video assembly
    COMPLETE = "complete"  # Project complete


@dataclass
class VideoSegment:
    """A single segment/scene in the storyboard."""

    segment_id: str
    description: str
    prompt: str = ""
    duration_sec: float = 5.0
    transition: str = "cut"
    key_elements: List[str] = field(default_factory=list)
    keyframe_image_url: Optional[str] = None
    selected_video_url: Optional[str] = None
    video_variants: List[str] = field(default_factory=list)  # URLs of generated variants
    selected_variant_index: Optional[int] = None
    video_model: str = "sora"  # sora, veo, or kling


@dataclass
class VideoProjectState:
    """State for a video generation project."""

    title: str = "Untitled Project"
    phase: ProjectPhase = ProjectPhase.CLARIFYING

    # Input specifications
    aspect_ratio: str = "9:16"  # Portrait default per CLAUDE.md
    target_duration_sec: int = 30
    description: str = ""
    reference_video_url: Optional[str] = None
    reference_images: List[str] = field(default_factory=list)

    # Storyboard
    segments: List[VideoSegment] = field(default_factory=list)
    storyboard_approved: bool = False

    # Outputs
    final_video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    banner_url: Optional[str] = None
    marketing_copy: Optional[str] = None

    # Metadata
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()

    def set_phase(self, phase: ProjectPhase) -> None:
        """Set the current workflow phase."""
        self.phase = phase
        self.touch()

    def set_storyboard(self, segments: List[VideoSegment]) -> None:
        """Set the storyboard segments."""
        self.segments = segments
        self.phase = ProjectPhase.STORYBOARD
        self.touch()

    def approve_storyboard(self) -> None:
        """Mark storyboard as approved and move to generation phase."""
        self.storyboard_approved = True
        self.phase = ProjectPhase.GENERATING
        self.touch()

    def select_variant(self, segment_id: str, variant_index: int) -> None:
        """Select a video variant for a segment."""
        for seg in self.segments:
            if seg.segment_id == segment_id:
                seg.selected_variant_index = variant_index
                if seg.video_variants and 0 <= variant_index < len(seg.video_variants):
                    seg.selected_video_url = seg.video_variants[variant_index]
                break
        self.touch()

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
        self.phase = ProjectPhase.COMPLETE
        self.touch()

    def clone(self) -> "VideoProjectState":
        """Create a copy of this state."""
        return replace(self)

    def to_payload(self, thread_id: str | None = None) -> dict[str, Any]:
        """Convert state to JSON-serializable payload for frontend."""
        payload: dict[str, Any] = {
            "title": self.title,
            "phase": self.phase.value,
            "aspectRatio": self.aspect_ratio,
            "targetDurationSec": self.target_duration_sec,
            "description": self.description,
            "referenceVideoUrl": self.reference_video_url,
            "referenceImages": self.reference_images,
            "segments": [
                {
                    "segmentId": seg.segment_id,
                    "description": seg.description,
                    "prompt": seg.prompt,
                    "durationSec": seg.duration_sec,
                    "transition": seg.transition,
                    "keyElements": seg.key_elements,
                    "keyframeImageUrl": seg.keyframe_image_url,
                    "selectedVideoUrl": seg.selected_video_url,
                    "videoVariants": seg.video_variants,
                    "selectedVariantIndex": seg.selected_variant_index,
                    "videoModel": seg.video_model,
                }
                for seg in self.segments
            ],
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
