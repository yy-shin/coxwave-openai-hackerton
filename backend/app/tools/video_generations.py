"""Video generation tool that converts VideoProjectState to VideoGenerations."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.integrations.video_generation import (
    GeneratedVideo,
    GenerationConfig,
    GenerationResult,
    ImageInput,
    SoraInput,
    VeoInput,
    VideoGenerationInput,
    VideoGenerationService,
)
from app.video_project_state import GenerationInput, ReferenceImage, VideoProjectState


class SegmentGeneration(BaseModel):
    """Video generation results for a single storyboard segment."""

    segment_index: int = Field(..., ge=0, description="Index of the segment in the storyboard")
    scene_description: str | None = Field(None, description="Description of the scene")
    status: Literal["pending", "in_progress", "completed", "failed"] = Field(
        "pending", description="Status of this segment's video generation"
    )
    generation_results: list[GenerationResult] = Field(
        default_factory=list, description="Results for each generation input"
    )


class VideoGenerations(BaseModel):
    """Container for video generation results linked to a project."""

    project_id: str = Field(..., description="Unique identifier for the project")
    created_at: str = Field(..., description="ISO 8601 timestamp when generation started")
    status: Literal["pending", "in_progress", "completed", "failed"] = Field(
        "pending", description="Overall status of video generation"
    )
    segments: list[SegmentGeneration] = Field(
        default_factory=list, description="Generation results for each segment"
    )


def _convert_reference_image_to_image_input(ref_image: ReferenceImage) -> ImageInput:
    """Convert a ReferenceImage to ImageInput."""
    return ImageInput(url=ref_image.url)


def _convert_generation_input_to_provider_input(
    gen_input: GenerationInput,
) -> VideoGenerationInput:
    """Convert GenerationInput from VideoProjectState to SoraInput or VeoInput."""
    provider = gen_input.provider

    # Convert input_image if present
    input_image: ImageInput | None = None
    if gen_input.input_image:
        input_image = _convert_reference_image_to_image_input(gen_input.input_image)

    if provider == "sora":
        return SoraInput(
            provider="sora",
            prompt=gen_input.prompt,
            input_image=input_image,
        )
    elif provider == "veo":
        # Convert reference_images if present
        reference_images: list[ImageInput] | None = None
        if gen_input.reference_images:
            reference_images = [
                _convert_reference_image_to_image_input(img)
                for img in gen_input.reference_images
            ]

        return VeoInput(
            provider="veo",
            prompt=gen_input.prompt,
            input_image=input_image,
            negative_prompt=gen_input.negative_prompt,
            reference_images=reference_images,
        )
    else:
        # For unsupported providers (like "kling"), default to veo
        return VeoInput(
            provider="veo",
            prompt=gen_input.prompt,
            input_image=input_image,
            negative_prompt=gen_input.negative_prompt,
        )


def _derive_segment_status(
    results: list[GenerationResult],
) -> Literal["pending", "in_progress", "completed", "failed"]:
    """Derive segment status from generation results."""
    if not results:
        return "pending"

    statuses = [r.video.status for r in results]

    if all(s == "completed" for s in statuses):
        return "completed"
    if any(s == "failed" for s in statuses):
        return "failed"
    if any(s in ("in_progress", "queued") for s in statuses):
        return "in_progress"
    return "pending"


def _derive_overall_status(
    segments: list[SegmentGeneration],
) -> Literal["pending", "in_progress", "completed", "failed"]:
    """Derive overall status from segment statuses."""
    if not segments:
        return "pending"

    statuses = [s.status for s in segments]

    if all(s == "completed" for s in statuses):
        return "completed"
    if any(s == "failed" for s in statuses):
        return "failed"
    if any(s == "in_progress" for s in statuses):
        return "in_progress"
    return "pending"


def _get_validated_duration(duration: float) -> int:
    """Convert and validate duration to an integer supported by providers."""
    # Round to nearest supported duration (4, 6, 8)
    duration_int = int(round(duration))
    supported = [4, 6, 8]
    return min(supported, key=lambda x: abs(x - duration_int))


async def generate_videos_from_project(
    project_id: str,
    state: VideoProjectState,
    wait_for_completion: bool = False,
    service: VideoGenerationService | None = None,
) -> VideoGenerations:
    """
    Generate videos for all segments in a VideoProjectState.

    Args:
        project_id: Unique identifier for this project
        state: The VideoProjectState containing storyboard
        wait_for_completion: If True, poll until all videos complete
        service: Optional VideoGenerationService instance. Creates one if not provided.

    Returns:
        VideoGenerations with results for each segment
    """
    if service is None:
        service = VideoGenerationService()

    created_at = datetime.now(UTC).isoformat()

    # Build segments list
    segments: list[SegmentGeneration] = []

    for segment_index, segment in enumerate(state.storyboard.segments):
        # Build GenerationConfig from segment duration and project aspect ratio
        duration = _get_validated_duration(segment.duration)
        aspect_ratio = state.aspect_ratio if state.aspect_ratio in ("16:9", "9:16") else "9:16"
        config = GenerationConfig(
            duration=duration,
            aspect_ratio=aspect_ratio,  # type: ignore
        )

        # Convert all generation inputs and call API
        inputs_with_indices: list[tuple[VideoGenerationInput, int]] = []
        for input_index, gen_input in enumerate(segment.generation_inputs):
            provider_input = _convert_generation_input_to_provider_input(gen_input)
            inputs_with_indices.append((provider_input, input_index))

        # Generate videos in batch
        if inputs_with_indices:
            results = await service.generate_batch(inputs_with_indices, config)
        else:
            results = []

        # Derive segment status
        segment_status = _derive_segment_status(results)

        segments.append(
            SegmentGeneration(
                segment_index=segment_index,
                scene_description=segment.scene_description,
                status=segment_status,
                generation_results=results,
            )
        )

    # Wait for completion if requested
    if wait_for_completion and segments:
        # Collect all video IDs to wait for
        videos_to_wait: list[tuple[Literal["sora", "veo"], str, int]] = []
        for seg in segments:
            for result in seg.generation_results:
                videos_to_wait.append(
                    (result.provider, result.video.id, result.input_index)
                )

        if videos_to_wait:
            completed_results = await service.wait_for_batch(videos_to_wait)

            # Update results with completed statuses
            result_map = {
                (r.provider, r.video.id): r for r in completed_results
            }

            for seg in segments:
                updated_results = []
                for result in seg.generation_results:
                    key = (result.provider, result.video.id)
                    if key in result_map:
                        updated_results.append(result_map[key])
                    else:
                        updated_results.append(result)
                seg.generation_results = updated_results
                seg.status = _derive_segment_status(updated_results)

    # Derive overall status
    overall_status = _derive_overall_status(segments)

    return VideoGenerations(
        project_id=project_id,
        created_at=created_at,
        status=overall_status,
        segments=segments,
    )
