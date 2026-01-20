"""Tests for generate_videos_from_project function."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.integrations.video_generation import (
    GeneratedVideo,
    GenerationConfig,
    GenerationResult,
    VeoInput,
    VideoGenerationService,
)
from app.tools.video_generations import generate_videos_from_project, VideoGenerations
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
