"""Tests for generate_videos_from_project function."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.video_generation import (
    GeneratedVideo,
    GenerationConfig,
    GenerationResult,
    VeoInput,
    VideoGenerationService,
)
from app.tools.video_generations import (
    generate_videos_from_project,
    get_video_local_path,
    poll_and_save_video_generations,
    SegmentGeneration,
    VideoGenerations,
)
from app.video_project_state import (
    GenerationInput,
    ImageInput,
    Segment,
    Storyboard,
    VideoProjectState,
)


class TestGenerateVideosFromProject:
    """Tests for generate_videos_from_project function."""

    @pytest.mark.asyncio
    async def test_generate_videos_single_segment(self, mock_all_api_keys):
        """Test video generation with single segment and one veo input, 9:16 aspect ratio."""
        # Arrange: Create a VideoProjectState with one segment containing one veo input
        state = VideoProjectState(
            title="Test Project",
            description="Test description",
            aspect_ratio="9:16",
            total_duration=8,
            storyboard=Storyboard(
                segments=[
                    Segment(
                        scene_description="Opening shot: Cookie character appears",
                        duration=8.0,
                        generation_inputs=[
                            GenerationInput(
                                provider="veo",
                                prompt="A cookie character appearing in a magical forest",
                            ),
                        ],
                    ),
                ]
            ),
        )

        # Mock the GeneratedVideo response
        mock_video = GeneratedVideo(
            id="veo_gen_001",
            status="queued",
            created_at="2025-01-20T10:30:00Z",
            duration=8,
            resolution="720p",
            has_audio=True,
        )

        mock_result = GenerationResult(
            input_index=0,
            provider="veo",
            video=mock_video,
        )

        # Create a mock service
        mock_service = MagicMock(spec=VideoGenerationService)
        mock_service.generate_batch = AsyncMock(return_value=[mock_result])

        # Act
        result = await generate_videos_from_project(
            project_id="project_001",
            state=state,
            service=mock_service,
        )

        # Assert: Check the VideoGenerations structure
        assert isinstance(result, VideoGenerations)
        assert result.project_id == "project_001"
        assert result.created_at is not None
        assert result.status == "in_progress"  # queued maps to in_progress at segment level

        # Check segments
        assert len(result.segments) == 1
        segment = result.segments[0]
        assert segment.segment_index == 0
        assert segment.scene_description == "Opening shot: Cookie character appears"
        assert segment.status == "in_progress"

        # Check generation results
        assert len(segment.generation_results) == 1
        gen_result = segment.generation_results[0]
        assert gen_result.input_index == 0
        assert gen_result.provider == "veo"
        assert gen_result.video.id == "veo_gen_001"
        assert gen_result.video.status == "queued"

        # Verify generate_batch was called with correct config
        mock_service.generate_batch.assert_called_once()
        call_args = mock_service.generate_batch.call_args
        inputs, config = call_args[0]
        assert len(inputs) == 1
        assert config.aspect_ratio == "9:16"
        assert config.duration == 8

    @pytest.mark.asyncio
    async def test_generate_videos_multiple_segments(self, mock_all_api_keys):
        """Test video generation with multiple segments and multiple inputs, 9:16 aspect ratio."""
        # Arrange: Create a VideoProjectState with multiple segments
        state = VideoProjectState(
            title="Multi-Segment Project",
            description="Test with multiple segments",
            aspect_ratio="9:16",
            total_duration=24,
            storyboard=Storyboard(
                segments=[
                    Segment(
                        scene_description="Opening: Character introduction",
                        duration=8.0,
                        generation_inputs=[
                            GenerationInput(
                                provider="veo",
                                prompt="Character walks into frame",
                            ),
                            GenerationInput(
                                provider="veo",
                                prompt="Character waves at camera",
                                input_image=ImageInput(file_path="https://example.com/ref.jpg"),
                            ),
                        ],
                    ),
                    Segment(
                        scene_description="Middle: Action sequence",
                        duration=8.0,
                        generation_inputs=[
                            GenerationInput(
                                provider="veo",
                                prompt="Dramatic action shot",
                            ),
                        ],
                    ),
                    Segment(
                        scene_description="Ending: Logo reveal",
                        duration=8.0,
                        generation_inputs=[
                            GenerationInput(
                                provider="veo",
                                prompt="Logo appears with sparkles",
                            ),
                        ],
                    ),
                ]
            ),
        )

        # Create mock videos for each segment
        mock_videos_segment_0 = [
            GenerationResult(
                input_index=0,
                provider="veo",
                video=GeneratedVideo(
                    id="veo_seg0_input0",
                    status="queued",
                    created_at="2025-01-20T10:30:00Z",
                    duration=8,
                ),
            ),
            GenerationResult(
                input_index=1,
                provider="veo",
                video=GeneratedVideo(
                    id="veo_seg0_input1",
                    status="queued",
                    created_at="2025-01-20T10:30:00Z",
                    duration=8,
                ),
            ),
        ]

        mock_videos_segment_1 = [
            GenerationResult(
                input_index=0,
                provider="veo",
                video=GeneratedVideo(
                    id="veo_seg1_input0",
                    status="completed",
                    created_at="2025-01-20T10:30:00Z",
                    duration=8,
                    video_url="https://storage.example.com/video1.mp4",
                ),
            ),
        ]

        mock_videos_segment_2 = [
            GenerationResult(
                input_index=0,
                provider="veo",
                video=GeneratedVideo(
                    id="veo_seg2_input0",
                    status="queued",
                    created_at="2025-01-20T10:30:00Z",
                    duration=8,
                ),
            ),
        ]

        # Create a mock service that returns different results per call
        mock_service = MagicMock(spec=VideoGenerationService)
        mock_service.generate_batch = AsyncMock(
            side_effect=[mock_videos_segment_0, mock_videos_segment_1, mock_videos_segment_2]
        )

        # Act
        result = await generate_videos_from_project(
            project_id="project_multi",
            state=state,
            service=mock_service,
        )

        # Assert: Check the VideoGenerations structure
        assert isinstance(result, VideoGenerations)
        assert result.project_id == "project_multi"
        assert result.created_at is not None
        # Overall status is in_progress because not all are completed
        assert result.status == "in_progress"

        # Check all three segments
        assert len(result.segments) == 3

        # Segment 0: Two inputs, both queued -> in_progress
        seg0 = result.segments[0]
        assert seg0.segment_index == 0
        assert seg0.scene_description == "Opening: Character introduction"
        assert seg0.status == "in_progress"
        assert len(seg0.generation_results) == 2
        assert seg0.generation_results[0].video.id == "veo_seg0_input0"
        assert seg0.generation_results[1].video.id == "veo_seg0_input1"
        assert seg0.generation_results[1].input_index == 1

        # Segment 1: One input, completed
        seg1 = result.segments[1]
        assert seg1.segment_index == 1
        assert seg1.scene_description == "Middle: Action sequence"
        assert seg1.status == "completed"
        assert len(seg1.generation_results) == 1
        assert seg1.generation_results[0].video.status == "completed"
        assert seg1.generation_results[0].video.video_url == "https://storage.example.com/video1.mp4"

        # Segment 2: One input, queued -> in_progress
        seg2 = result.segments[2]
        assert seg2.segment_index == 2
        assert seg2.scene_description == "Ending: Logo reveal"
        assert seg2.status == "in_progress"
        assert len(seg2.generation_results) == 1

        # Verify generate_batch was called three times (once per segment)
        assert mock_service.generate_batch.call_count == 3

        # Verify all calls used 9:16 aspect ratio
        for call in mock_service.generate_batch.call_args_list:
            config = call[0][1]
            assert config.aspect_ratio == "9:16"


class TestGetVideoLocalPath:
    """Tests for get_video_local_path function."""

    def test_get_video_local_path_basic(self):
        """Test basic path generation."""
        path = get_video_local_path(
            project_root="/projects",
            project_id="proj_001",
            segment_index=0,
            input_index=0,
            video_id="video_abc123",
        )
        expected = Path(
            "/projects/data/video_generations_result_proj_001/"
            "segment_0/generation_result_0/generated_video_video_abc123.mp4"
        )
        assert path == expected

    def test_get_video_local_path_different_indices(self):
        """Test path generation with different segment and input indices."""
        path = get_video_local_path(
            project_root=Path("/tmp/test"),
            project_id="project_xyz",
            segment_index=2,
            input_index=3,
            video_id="veo_gen_456",
        )
        expected = Path(
            "/tmp/test/data/video_generations_result_project_xyz/"
            "segment_2/generation_result_3/generated_video_veo_gen_456.mp4"
        )
        assert path == expected

    def test_get_video_local_path_accepts_string_or_path(self):
        """Test that both string and Path are accepted for project_root."""
        # String input
        path1 = get_video_local_path("/root", "proj", 0, 0, "vid")
        # Path input
        path2 = get_video_local_path(Path("/root"), "proj", 0, 0, "vid")
        assert path1 == path2


class TestPollAndSaveVideoGenerations:
    """Tests for poll_and_save_video_generations function."""

    @pytest.mark.asyncio
    async def test_poll_updates_status_from_queued_to_completed(
        self, mock_all_api_keys, tmp_path
    ):
        """Test that polling updates video status from queued to completed."""
        # Arrange: Create initial VideoGenerations with a queued video
        initial_video = GeneratedVideo(
            id="veo_gen_001",
            status="queued",
            created_at="2025-01-20T10:30:00Z",
            duration=8,
        )
        video_generations = VideoGenerations(
            project_id="project_001",
            created_at="2025-01-20T10:30:00Z",
            status="in_progress",
            segments=[
                SegmentGeneration(
                    segment_index=0,
                    scene_description="Test scene",
                    status="in_progress",
                    generation_results=[
                        GenerationResult(
                            input_index=0,
                            provider="veo",
                            video=initial_video,
                        )
                    ],
                )
            ],
        )

        # Mock service returns completed status with video_url
        completed_video = GeneratedVideo(
            id="veo_gen_001",
            status="completed",
            created_at="2025-01-20T10:30:00Z",
            duration=8,
            video_url="https://storage.example.com/video.mp4",
        )
        mock_service = MagicMock(spec=VideoGenerationService)
        mock_service.get_status = AsyncMock(return_value=completed_video)

        # Mock the download
        with patch(
            "app.tools.video_generations._download_video",
            new_callable=AsyncMock,
            return_value=None,
        ) as mock_download:
            # Act
            result = await poll_and_save_video_generations(
                video_generations=video_generations,
                project_root=tmp_path,
                service=mock_service,
            )

        # Assert
        assert result.status == "completed"
        assert len(result.segments) == 1
        assert result.segments[0].status == "completed"
        assert result.segments[0].generation_results[0].video.status == "completed"
        assert (
            result.segments[0].generation_results[0].video.video_url
            == "https://storage.example.com/video.mp4"
        )

        # Verify get_status was called
        mock_service.get_status.assert_called_once_with("veo", "veo_gen_001")

        # Verify download was attempted
        mock_download.assert_called_once()

    @pytest.mark.asyncio
    async def test_poll_does_not_check_already_completed(
        self, mock_all_api_keys, tmp_path
    ):
        """Test that already completed videos are not checked again."""
        # Arrange: Create VideoGenerations with already completed video
        completed_video = GeneratedVideo(
            id="veo_gen_001",
            status="completed",
            created_at="2025-01-20T10:30:00Z",
            duration=8,
            video_url="https://storage.example.com/video.mp4",
        )
        video_generations = VideoGenerations(
            project_id="project_001",
            created_at="2025-01-20T10:30:00Z",
            status="completed",
            segments=[
                SegmentGeneration(
                    segment_index=0,
                    scene_description="Test scene",
                    status="completed",
                    generation_results=[
                        GenerationResult(
                            input_index=0,
                            provider="veo",
                            video=completed_video,
                        )
                    ],
                )
            ],
        )

        mock_service = MagicMock(spec=VideoGenerationService)
        mock_service.get_status = AsyncMock()

        # Pre-create the file to simulate already downloaded
        local_path = get_video_local_path(
            tmp_path, "project_001", 0, 0, "veo_gen_001"
        )
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(b"fake video content")

        # Act
        result = await poll_and_save_video_generations(
            video_generations=video_generations,
            project_root=tmp_path,
            service=mock_service,
        )

        # Assert: get_status should NOT be called for completed videos
        mock_service.get_status.assert_not_called()

        # Result should remain completed
        assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_poll_handles_status_check_error(self, mock_all_api_keys, tmp_path):
        """Test that status check errors are handled gracefully."""
        # Arrange
        initial_video = GeneratedVideo(
            id="veo_gen_001",
            status="in_progress",
            progress=50,
            created_at="2025-01-20T10:30:00Z",
        )
        video_generations = VideoGenerations(
            project_id="project_001",
            created_at="2025-01-20T10:30:00Z",
            status="in_progress",
            segments=[
                SegmentGeneration(
                    segment_index=0,
                    scene_description="Test scene",
                    status="in_progress",
                    generation_results=[
                        GenerationResult(
                            input_index=0,
                            provider="veo",
                            video=initial_video,
                        )
                    ],
                )
            ],
        )

        # Mock service raises an exception
        mock_service = MagicMock(spec=VideoGenerationService)
        mock_service.get_status = AsyncMock(side_effect=Exception("API Error"))

        # Act
        result = await poll_and_save_video_generations(
            video_generations=video_generations,
            project_root=tmp_path,
            service=mock_service,
        )

        # Assert: Error should be captured in the video's error field
        assert "Status check failed" in result.segments[0].generation_results[0].video.error

    @pytest.mark.asyncio
    async def test_poll_handles_download_error(self, mock_all_api_keys, tmp_path):
        """Test that download errors are handled gracefully."""
        # Arrange
        initial_video = GeneratedVideo(
            id="veo_gen_001",
            status="queued",
            created_at="2025-01-20T10:30:00Z",
        )
        video_generations = VideoGenerations(
            project_id="project_001",
            created_at="2025-01-20T10:30:00Z",
            status="in_progress",
            segments=[
                SegmentGeneration(
                    segment_index=0,
                    scene_description="Test scene",
                    status="in_progress",
                    generation_results=[
                        GenerationResult(
                            input_index=0,
                            provider="veo",
                            video=initial_video,
                        )
                    ],
                )
            ],
        )

        # Mock service returns completed with URL
        completed_video = GeneratedVideo(
            id="veo_gen_001",
            status="completed",
            created_at="2025-01-20T10:30:00Z",
            video_url="https://storage.example.com/video.mp4",
        )
        mock_service = MagicMock(spec=VideoGenerationService)
        mock_service.get_status = AsyncMock(return_value=completed_video)

        # Mock download to fail
        with patch(
            "app.tools.video_generations._download_video",
            new_callable=AsyncMock,
            return_value="HTTP error 404: Not found",
        ):
            # Act
            result = await poll_and_save_video_generations(
                video_generations=video_generations,
                project_root=tmp_path,
                service=mock_service,
            )

        # Assert: Status should be completed but with download error
        video_result = result.segments[0].generation_results[0].video
        assert video_result.status == "completed"
        assert "Download failed" in video_result.error

    @pytest.mark.asyncio
    async def test_poll_multiple_segments_parallel(self, mock_all_api_keys, tmp_path):
        """Test polling multiple segments with mixed statuses."""
        # Arrange: Create VideoGenerations with multiple segments
        video_generations = VideoGenerations(
            project_id="project_multi",
            created_at="2025-01-20T10:30:00Z",
            status="in_progress",
            segments=[
                SegmentGeneration(
                    segment_index=0,
                    scene_description="Segment 0",
                    status="in_progress",
                    generation_results=[
                        GenerationResult(
                            input_index=0,
                            provider="veo",
                            video=GeneratedVideo(
                                id="veo_seg0_vid0",
                                status="queued",
                                created_at="2025-01-20T10:30:00Z",
                            ),
                        ),
                        GenerationResult(
                            input_index=1,
                            provider="sora",
                            video=GeneratedVideo(
                                id="sora_seg0_vid1",
                                status="in_progress",
                                progress=75,
                                created_at="2025-01-20T10:30:00Z",
                            ),
                        ),
                    ],
                ),
                SegmentGeneration(
                    segment_index=1,
                    scene_description="Segment 1",
                    status="completed",
                    generation_results=[
                        GenerationResult(
                            input_index=0,
                            provider="veo",
                            video=GeneratedVideo(
                                id="veo_seg1_vid0",
                                status="completed",
                                created_at="2025-01-20T10:30:00Z",
                                video_url="https://storage.example.com/seg1.mp4",
                            ),
                        ),
                    ],
                ),
            ],
        )

        # Mock service to return different statuses
        async def mock_get_status(provider, video_id):
            if video_id == "veo_seg0_vid0":
                return GeneratedVideo(
                    id="veo_seg0_vid0",
                    status="completed",
                    created_at="2025-01-20T10:30:00Z",
                    video_url="https://storage.example.com/seg0_vid0.mp4",
                )
            elif video_id == "sora_seg0_vid1":
                return GeneratedVideo(
                    id="sora_seg0_vid1",
                    status="in_progress",
                    progress=90,
                    created_at="2025-01-20T10:30:00Z",
                )
            raise ValueError(f"Unexpected video_id: {video_id}")

        mock_service = MagicMock(spec=VideoGenerationService)
        mock_service.get_status = AsyncMock(side_effect=mock_get_status)

        # Pre-create file for seg1 (already completed)
        seg1_path = get_video_local_path(
            tmp_path, "project_multi", 1, 0, "veo_seg1_vid0"
        )
        seg1_path.parent.mkdir(parents=True, exist_ok=True)
        seg1_path.write_bytes(b"existing video")

        # Mock download for newly completed video
        with patch(
            "app.tools.video_generations._download_video",
            new_callable=AsyncMock,
            return_value=None,
        ) as mock_download:
            # Act
            result = await poll_and_save_video_generations(
                video_generations=video_generations,
                project_root=tmp_path,
                service=mock_service,
            )

        # Assert
        # Overall status should still be in_progress (seg0 vid1 not done)
        assert result.status == "in_progress"

        # Segment 0: one completed, one in_progress
        seg0 = result.segments[0]
        assert seg0.status == "in_progress"
        assert seg0.generation_results[0].video.status == "completed"
        assert seg0.generation_results[1].video.status == "in_progress"
        assert seg0.generation_results[1].video.progress == 90

        # Segment 1: already completed, unchanged
        seg1 = result.segments[1]
        assert seg1.status == "completed"

        # Verify get_status was called for queued/in_progress only
        assert mock_service.get_status.call_count == 2

        # Verify download was called only for newly completed video
        mock_download.assert_called_once()


# ============================================================================
# Real Integration Tests (no mocks)
# ============================================================================


# Sample test image URLs - publicly accessible, stable URLs
# Using 9:16 aspect ratio (720x1280) to match video output dimensions
TEST_IMAGE_URLS = [
    "https://picsum.photos/seed/test1/720/1280",
    "https://picsum.photos/seed/test2/720/1280",
    "https://picsum.photos/seed/test3/720/1280",
]


async def _download_test_images(tmp_path: Path) -> list[str]:
    """Download test images to temporary local files.

    Returns list of local file paths.
    """
    import httpx

    local_paths = []
    async with httpx.AsyncClient() as client:
        for i, url in enumerate(TEST_IMAGE_URLS):
            response = await client.get(url, follow_redirects=True, timeout=30.0)
            response.raise_for_status()

            # Save to temp file
            local_path = tmp_path / f"test_image_{i}.jpg"
            local_path.write_bytes(response.content)
            local_paths.append(str(local_path))

    return local_paths


def _create_test_video_project_state(image_paths: list[str]) -> VideoProjectState:
    """Create a VideoProjectState with 7 segments × 3 inputs = 21 generations.

    Args:
        image_paths: List of local file paths to test images (9:16 aspect ratio).

    Uses varied configurations across both Veo and Sora providers:
    - input_image: first-frame image for Sora (local file paths)
    - negative_prompt: what to avoid in generation (Veo only)

    Note: Veo requires GCS URIs (gs://...) or base64 for images, so we only
    use text prompts and negative_prompt for Veo in this test.

    Distribution: 18 Sora + 3 Veo to stay within Veo rate limits.
    Veo requests are placed in segments 0, 3, and 6 to spread them out.
    """
    segments = [
        # Segment 0: Sora basic | Sora + input_image | Veo + negative_prompt
        Segment(
            scene_description="Opening: Character emerges from portal",
            duration=8.0,
            generation_inputs=[
                GenerationInput(
                    provider="sora",
                    prompt="A mystical character emerges from a glowing portal in a dark forest, cinematic lighting, smooth camera movement",
                ),
                GenerationInput(
                    provider="sora",
                    prompt="A mystical character emerges from a glowing portal in a dark forest, cinematic lighting, smooth camera movement",
                    input_image=ImageInput(file_path=image_paths[0]),
                ),
                GenerationInput(
                    provider="veo",
                    prompt="A mystical character emerges from a glowing portal in a dark forest, cinematic lighting, smooth camera movement",
                    negative_prompt="blurry, low quality, distorted, pixelated, artifacts",
                ),
            ],
        ),
        # Segment 1: Sora + input_image | Sora basic | Sora basic
        Segment(
            scene_description="Action: Character runs through enchanted landscape",
            duration=8.0,
            generation_inputs=[
                GenerationInput(
                    provider="sora",
                    prompt="Character runs through an enchanted landscape with floating crystals, dynamic camera tracking, vibrant colors",
                    input_image=ImageInput(file_path=image_paths[1]),
                ),
                GenerationInput(
                    provider="sora",
                    prompt="Character runs through an enchanted landscape with floating crystals, dynamic camera tracking, vibrant colors",
                ),
                GenerationInput(
                    provider="sora",
                    prompt="A character sprinting through a magical crystal forest, glowing particles in air",
                ),
            ],
        ),
        # Segment 2: Sora basic | Sora basic | Sora + input_image
        Segment(
            scene_description="Dramatic: Character faces challenge",
            duration=8.0,
            generation_inputs=[
                GenerationInput(
                    provider="sora",
                    prompt="Character faces a dramatic challenge with swirling energy, epic composition, golden hour lighting",
                ),
                GenerationInput(
                    provider="sora",
                    prompt="A hero confronting destiny, dramatic lighting, cinematic composition",
                ),
                GenerationInput(
                    provider="sora",
                    prompt="Character faces a dramatic challenge with swirling energy, epic composition, golden hour lighting",
                    input_image=ImageInput(file_path=image_paths[2]),
                ),
            ],
        ),
        # Segment 3: Sora basic | Sora + input_image | Veo + negative_prompt
        Segment(
            scene_description="Transformation: Character powers up",
            duration=8.0,
            generation_inputs=[
                GenerationInput(
                    provider="sora",
                    prompt="Character undergoes magical transformation with particle effects, bright aura, smooth transition",
                ),
                GenerationInput(
                    provider="sora",
                    prompt="Character undergoes magical transformation with particle effects, bright aura, smooth transition",
                    input_image=ImageInput(file_path=image_paths[0]),
                ),
                GenerationInput(
                    provider="veo",
                    prompt="Character undergoes magical transformation with particle effects, bright aura, smooth transition",
                    negative_prompt="jerky motion, low resolution, noise, grain",
                ),
            ],
        ),
        # Segment 4: Sora basic | Sora basic | Sora + input_image
        Segment(
            scene_description="Victory: Character triumphs",
            duration=8.0,
            generation_inputs=[
                GenerationInput(
                    provider="sora",
                    prompt="Character celebrates victory with fireworks and confetti, joyful atmosphere, slow motion",
                ),
                GenerationInput(
                    provider="sora",
                    prompt="Celebration scene with colorful fireworks exploding in the night sky, slow motion",
                ),
                GenerationInput(
                    provider="sora",
                    prompt="Victory celebration with confetti and sparkles, joyful atmosphere",
                    input_image=ImageInput(file_path=image_paths[1]),
                ),
            ],
        ),
        # Segment 5: Sora + input_image | Sora basic | Sora basic
        Segment(
            scene_description="Epilogue: Character looks to the horizon",
            duration=8.0,
            generation_inputs=[
                GenerationInput(
                    provider="sora",
                    prompt="Character gazes at a beautiful sunset horizon, peaceful atmosphere, cinematic wide shot",
                    input_image=ImageInput(file_path=image_paths[2]),
                ),
                GenerationInput(
                    provider="sora",
                    prompt="Character gazes at a beautiful sunset horizon, peaceful atmosphere, cinematic wide shot",
                ),
                GenerationInput(
                    provider="sora",
                    prompt="Silhouette against sunset, peaceful ending, golden light",
                ),
            ],
        ),
        # Segment 6: Sora basic | Sora + input_image | Veo + negative_prompt
        Segment(
            scene_description="Finale: Logo reveal with special effects",
            duration=8.0,
            generation_inputs=[
                GenerationInput(
                    provider="sora",
                    prompt="Dramatic logo reveal with sparkling particles and light rays, professional quality, brand focused",
                ),
                GenerationInput(
                    provider="sora",
                    prompt="Dramatic logo reveal with sparkling particles and light rays, professional quality, brand focused",
                    input_image=ImageInput(file_path=image_paths[0]),
                ),
                GenerationInput(
                    provider="veo",
                    prompt="Dramatic logo reveal with sparkling particles and light rays, professional quality, brand focused",
                    negative_prompt="amateur, cheap, pixelated, blurry text",
                ),
            ],
        ),
    ]

    return VideoProjectState(
        title="Real Integration Test Project",
        description="Test project with 21 video generations across Veo and Sora",
        aspect_ratio="9:16",
        total_duration=56,  # 7 segments × 8 seconds
        storyboard=Storyboard(segments=segments),
    )


@pytest.mark.integration
class TestRealVideoGenerationIntegration:
    """Real integration tests that call actual video generation APIs.

    These tests require valid API keys in the environment:
    - OPENAI_API_KEY: For Sora video generation
    - GOOGLE_API_KEY: For Veo video generation

    Run with: uv run pytest tests/test_video_generations.py::TestRealVideoGenerationIntegration -v -s
    """

    @pytest.mark.asyncio
    async def test_generate_21_videos_with_full_parameter_coverage(self, tmp_path):
        """Test generating 21 videos with both Veo and Sora, using all parameter types.

        This test:
        1. Downloads test images to local temp files
        2. Creates a VideoProjectState with 7 segments × 3 inputs = 21 generations
        3. Uses both Veo and Sora providers with varied configurations
        4. Includes input_image (Sora) and negative_prompt (Veo) fields
        5. Calls real APIs to generate videos
        6. Polls until all complete (up to ~20 minutes)
        7. Downloads all videos to disk
        8. Verifies files exist with non-zero size
        """
        # Arrange: Download test images to local temp files
        print("\n=== Downloading test images ===")
        image_paths = await _download_test_images(tmp_path)
        print(f"Downloaded {len(image_paths)} test images")

        # Create test project state with local image paths
        state = _create_test_video_project_state(image_paths)
        project_id = "integration_test_21_videos"

        # Verify we have 21 generation inputs
        total_inputs = sum(
            len(seg.generation_inputs) for seg in state.storyboard.segments
        )
        assert total_inputs == 21, f"Expected 21 inputs, got {total_inputs}"

        # Act: Generate videos (real API calls)
        print("\n=== Starting video generation for 21 videos ===")
        video_generations = await generate_videos_from_project(
            project_id=project_id,
            state=state,
        )

        # Verify initial structure
        assert isinstance(video_generations, VideoGenerations)
        assert video_generations.project_id == project_id
        assert len(video_generations.segments) == 7

        total_videos = sum(
            len(seg.generation_results) for seg in video_generations.segments
        )
        assert total_videos == 21, f"Expected 21 generation results, got {total_videos}"

        # Poll until completion
        max_polls = 120  # ~20 minutes with 10s intervals
        poll_interval = 10  # seconds
        polls = 0

        print(f"Initial status: {video_generations.status}")

        while video_generations.status != "completed" and polls < max_polls:
            await asyncio.sleep(poll_interval)
            video_generations = await poll_and_save_video_generations(
                video_generations, tmp_path
            )
            polls += 1

            # Calculate progress
            completed_count = sum(
                1
                for seg in video_generations.segments
                for r in seg.generation_results
                if r.video.status == "completed"
            )
            failed_count = sum(
                1
                for seg in video_generations.segments
                for r in seg.generation_results
                if r.video.status == "failed"
            )
            in_progress_count = sum(
                1
                for seg in video_generations.segments
                for r in seg.generation_results
                if r.video.status in ("queued", "in_progress")
            )

            print(
                f"Poll {polls}: {completed_count}/21 completed, "
                f"{in_progress_count} in progress, {failed_count} failed"
            )

            # Early exit if all have terminal status
            if completed_count + failed_count == 21:
                break

        # Assert: Final status checks
        print(f"\n=== Final status: {video_generations.status} ===")

        # Count final results
        final_completed = 0
        final_failed = 0
        for seg_idx, segment in enumerate(video_generations.segments):
            for res in segment.generation_results:
                if res.video.status == "completed":
                    final_completed += 1
                    print(
                        f"  Segment {seg_idx}, Input {res.input_index} "
                        f"({res.provider}): completed - {res.video.id}"
                    )
                elif res.video.status == "failed":
                    final_failed += 1
                    print(
                        f"  Segment {seg_idx}, Input {res.input_index} "
                        f"({res.provider}): FAILED - {res.video.error}"
                    )

        print(f"\nTotal: {final_completed} completed, {final_failed} failed")

        # Verify overall completion (allow some failures but most should complete)
        assert video_generations.status == "completed", (
            f"Expected 'completed' status, got '{video_generations.status}'. "
            f"Completed: {final_completed}, Failed: {final_failed}"
        )

        # Verify all videos completed
        assert final_completed == 21, (
            f"Expected 21 completed videos, got {final_completed}. "
            f"Failed: {final_failed}"
        )

        # Verify downloaded files exist with non-zero size
        downloaded_files = []
        for segment in video_generations.segments:
            for result in segment.generation_results:
                if result.video.status == "completed":
                    local_path = get_video_local_path(
                        tmp_path,
                        project_id,
                        segment.segment_index,
                        result.input_index,
                        result.video.id,
                    )
                    downloaded_files.append(local_path)

                    assert local_path.exists(), f"Video file not found: {local_path}"
                    file_size = local_path.stat().st_size
                    assert file_size > 0, (
                        f"Video file is empty: {local_path} (size: {file_size})"
                    )
                    print(f"  ✓ {local_path.name}: {file_size / 1024 / 1024:.2f} MB")

        print(f"\n=== Successfully downloaded {len(downloaded_files)} videos ===")
        assert len(downloaded_files) == 21
