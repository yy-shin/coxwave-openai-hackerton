"""Tests for generate_videos_from_project function."""

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
    ReferenceImage,
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
                                input_image=ReferenceImage(url="https://example.com/ref.jpg"),
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
