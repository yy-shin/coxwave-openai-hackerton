"""Video generation tool that converts VideoProjectState to VideoGenerations."""

import asyncio
import base64
import mimetypes
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import httpx
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
from app.video_project_state import GenerationInput, ImageInput as ProjectImageInput, VideoProjectState


class SegmentGeneration(BaseModel):
    """Video generation results for a single storyboard segment."""

    segment_index: int = Field(
        ..., ge=0, description="Index of the segment in the storyboard"
    )
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
    created_at: str = Field(
        ..., description="ISO 8601 timestamp when generation started"
    )
    status: Literal["pending", "in_progress", "completed", "failed"] = Field(
        "pending", description="Overall status of video generation"
    )
    segments: list[SegmentGeneration] = Field(
        default_factory=list, description="Generation results for each segment"
    )


def _convert_project_image_to_api_input(project_image: ProjectImageInput) -> ImageInput:
    """Convert a ProjectImageInput (file_path) to API ImageInput (base64).

    Reads the image file from the local file path and converts it to base64
    for sending to video generation providers.
    """
    file_path = project_image.file_path

    # Determine MIME type from file extension
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type not in ("image/jpeg", "image/png", "image/webp"):
        mime_type = "image/png"  # Default to PNG if unknown

    # Read file and encode as base64
    with open(file_path, "rb") as f:
        image_data = f.read()

    base64_data = base64.b64encode(image_data).decode("utf-8")

    return ImageInput(base64=base64_data, mime_type=mime_type)  # type: ignore


def _convert_generation_input_to_provider_input(
    gen_input: GenerationInput,
) -> VideoGenerationInput:
    """Convert GenerationInput from VideoProjectState to SoraInput or VeoInput."""
    provider = gen_input.provider

    # Convert input_image if present
    input_image: ImageInput | None = None
    if gen_input.input_image:
        input_image = _convert_project_image_to_api_input(gen_input.input_image)

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
                _convert_project_image_to_api_input(img)
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
        # For unsupported providers default to veo
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
        aspect_ratio = (
            state.aspect_ratio if state.aspect_ratio in ("16:9", "9:16") else "9:16"
        )
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
            result_map = {(r.provider, r.video.id): r for r in completed_results}

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


def get_video_local_path(
    project_root: Path | str,
    project_id: str,
    segment_index: int,
    input_index: int,
    video_id: str,
) -> Path:
    """
    Compute the local file path for a generated video.

    Output path structure:
    {project_root}/data/video_generations_result_{project_id}/
      segment_{segment_index}/
        generation_result_{input_index}/
          generated_video_{video_id}.mp4

    Args:
        project_root: Root directory for the project
        project_id: Unique identifier for the project
        segment_index: Index of the segment in the storyboard
        input_index: Index of the generation input within the segment
        video_id: Provider's unique video identifier

    Returns:
        Path to where the video should be saved
    """
    root = Path(project_root)
    return (
        root
        / "data"
        / f"video_generations_result_{project_id}"
        / f"segment_{segment_index}"
        / f"generation_result_{input_index}"
        / f"generated_video_{video_id}.mp4"
    )


async def _download_video(
    url: str,
    output_path: Path,
    provider: Literal["sora", "veo"],
    api_key: str | None = None,
) -> str | None:
    """
    Download video from URL to local path.

    Args:
        url: Video download URL
        output_path: Local path to save the video
        provider: Video generation provider ("sora" or "veo")
        api_key: API key for authentication (required for Sora)

    Returns:
        Error message on failure, None on success
    """
    try:
        # Create parent directories
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Build headers
        headers: dict[str, str] = {}
        if provider == "sora" and api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.get(url, headers=headers, follow_redirects=True)
            response.raise_for_status()

            # Write content to file
            with open(output_path, "wb") as f:
                f.write(response.content)

        return None
    except httpx.HTTPStatusError as e:
        return f"HTTP error {e.response.status_code}: {e.response.text[:200]}"
    except httpx.RequestError as e:
        return f"Request error: {str(e)}"
    except OSError as e:
        return f"File error: {str(e)}"


async def poll_and_save_video_generations(
    video_generations: VideoGenerations,
    project_root: Path | str,
    service: VideoGenerationService | None = None,
) -> VideoGenerations:
    """
    Check status of all video generations once and download completed videos.

    This function performs a single poll (no waiting/looping). Retry logic
    should be handled externally by the caller.

    Args:
        video_generations: Current VideoGenerations state to check
        project_root: Root directory for saving downloaded videos
        service: Optional VideoGenerationService instance. Creates one if not provided.

    Returns:
        Updated VideoGenerations with new statuses and downloaded videos
    """
    if service is None:
        service = VideoGenerationService()

    project_root = Path(project_root)
    project_id = video_generations.project_id

    # Get OpenAI API key for Sora downloads
    openai_api_key = os.environ.get("OPENAI_API_KEY")

    # Collect all videos that need status updates
    videos_to_check: list[tuple[int, int, GenerationResult]] = []
    for seg_idx, segment in enumerate(video_generations.segments):
        for res_idx, result in enumerate(segment.generation_results):
            if result.video.status in ("queued", "in_progress"):
                videos_to_check.append((seg_idx, res_idx, result))

    # Check statuses in parallel
    async def check_status(
        seg_idx: int, res_idx: int, result: GenerationResult
    ) -> tuple[int, int, GeneratedVideo | None, str | None]:
        try:
            updated_video = await service.get_status(result.provider, result.video.id)
            return (seg_idx, res_idx, updated_video, None)
        except Exception as e:
            return (seg_idx, res_idx, None, str(e))

    status_tasks = [
        check_status(seg_idx, res_idx, result)
        for seg_idx, res_idx, result in videos_to_check
    ]
    status_results = await asyncio.gather(*status_tasks)

    # Build a map of updated videos
    updated_videos: dict[tuple[int, int], GeneratedVideo] = {}
    for seg_idx, res_idx, updated_video, error in status_results:
        if updated_video:
            updated_videos[(seg_idx, res_idx)] = updated_video
        elif error:
            # Keep original video but add error
            for s_idx, segment in enumerate(video_generations.segments):
                if s_idx == seg_idx:
                    original = segment.generation_results[res_idx].video
                    updated_videos[(seg_idx, res_idx)] = original.model_copy(
                        update={"error": f"Status check failed: {error}"}
                    )

    # Collect videos that need downloading (completed with video_url but not yet downloaded)
    videos_to_download: list[tuple[int, int, GenerationResult, Path]] = []
    for seg_idx, segment in enumerate(video_generations.segments):
        for res_idx, result in enumerate(segment.generation_results):
            # Use updated video if available, otherwise original
            video = updated_videos.get((seg_idx, res_idx), result.video)
            local_path = get_video_local_path(
                project_root, project_id, seg_idx, result.input_index, video.id
            )
            if (
                video.status == "completed"
                and video.video_url
                and not local_path.exists()
            ):
                videos_to_download.append((seg_idx, res_idx, result, local_path))

    # Download videos in parallel
    async def download_one(
        seg_idx: int, res_idx: int, result: GenerationResult, local_path: Path
    ) -> tuple[int, int, str | None]:
        video = updated_videos.get((seg_idx, res_idx), result.video)
        api_key = openai_api_key if result.provider == "sora" else None
        error = await _download_video(
            video.video_url,  # type: ignore (we checked video_url is not None)
            local_path,
            result.provider,
            api_key,
        )
        return (seg_idx, res_idx, error)

    download_tasks = [
        download_one(seg_idx, res_idx, result, local_path)
        for seg_idx, res_idx, result, local_path in videos_to_download
    ]
    download_results = await asyncio.gather(*download_tasks)

    # Track download errors
    download_errors: dict[tuple[int, int], str] = {}
    for seg_idx, res_idx, error in download_results:
        if error:
            download_errors[(seg_idx, res_idx)] = error

    # Build updated VideoGenerations
    updated_segments: list[SegmentGeneration] = []
    for seg_idx, segment in enumerate(video_generations.segments):
        updated_results: list[GenerationResult] = []
        for res_idx, result in enumerate(segment.generation_results):
            key = (seg_idx, res_idx)

            # Get updated video (from status check) or original
            video = updated_videos.get(key, result.video)

            # Add download error if any
            if key in download_errors:
                video = video.model_copy(
                    update={"error": f"Download failed: {download_errors[key]}"}
                )

            updated_results.append(
                GenerationResult(
                    input_index=result.input_index,
                    provider=result.provider,
                    video=video,
                )
            )

        # Derive segment status
        segment_status = _derive_segment_status(updated_results)
        updated_segments.append(
            SegmentGeneration(
                segment_index=segment.segment_index,
                scene_description=segment.scene_description,
                status=segment_status,
                generation_results=updated_results,
            )
        )

    # Derive overall status
    overall_status = _derive_overall_status(updated_segments)

    return VideoGenerations(
        project_id=video_generations.project_id,
        created_at=video_generations.created_at,
        status=overall_status,
        segments=updated_segments,
    )
