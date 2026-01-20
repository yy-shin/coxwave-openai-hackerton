"""Tests for video generation Pydantic models."""

import pytest
from pydantic import ValidationError

from app.integrations.video_generation import (
    GeneratedVideo,
    GenerationConfig,
    GenerationResult,
    ImageInput,
    SoraInput,
    VeoInput,
)


class TestImageInput:
    """Tests for ImageInput model."""

    def test_url_input(self):
        """Test creating ImageInput with URL."""
        img = ImageInput(url="https://example.com/image.png")
        assert img.url == "https://example.com/image.png"
        assert img.base64 is None
        assert img.mime_type is None

    def test_base64_input(self):
        """Test creating ImageInput with base64."""
        img = ImageInput(
            base64="iVBORw0KGgo...",
            mime_type="image/png",
        )
        assert img.base64 == "iVBORw0KGgo..."
        assert img.mime_type == "image/png"
        assert img.url is None

    def test_valid_mime_types(self):
        """Test all valid mime types."""
        for mime in ["image/jpeg", "image/png", "image/webp"]:
            img = ImageInput(base64="data", mime_type=mime)
            assert img.mime_type == mime

    def test_invalid_mime_type(self):
        """Test invalid mime type raises error."""
        with pytest.raises(ValidationError):
            ImageInput(base64="data", mime_type="image/gif")


class TestSoraInput:
    """Tests for SoraInput model."""

    def test_minimal_input(self):
        """Test creating SoraInput with only required fields."""
        inp = SoraInput(prompt="A cat walking")
        assert inp.provider == "sora"
        assert inp.prompt == "A cat walking"
        assert inp.model is None
        assert inp.input_image is None

    def test_full_input(self):
        """Test creating SoraInput with all fields."""
        inp = SoraInput(
            provider="sora",
            model="sora-2-pro",
            prompt="A cat walking",
            input_image=ImageInput(url="https://example.com/cat.jpg"),
        )
        assert inp.provider == "sora"
        assert inp.model == "sora-2-pro"
        assert inp.input_image.url == "https://example.com/cat.jpg"

    def test_valid_models(self):
        """Test all valid Sora models."""
        for model in ["sora-2", "sora-2-pro"]:
            inp = SoraInput(prompt="test", model=model)
            assert inp.model == model

    def test_invalid_model(self):
        """Test invalid model raises error."""
        with pytest.raises(ValidationError):
            SoraInput(prompt="test", model="sora-1")

    def test_prompt_max_length(self):
        """Test prompt max length validation."""
        # Should work with 4096 chars
        inp = SoraInput(prompt="a" * 4096)
        assert len(inp.prompt) == 4096

        # Should fail with 4097 chars
        with pytest.raises(ValidationError):
            SoraInput(prompt="a" * 4097)


class TestVeoInput:
    """Tests for VeoInput model."""

    def test_minimal_input(self):
        """Test creating VeoInput with only required fields."""
        inp = VeoInput(prompt="A dog running")
        assert inp.provider == "veo"
        assert inp.prompt == "A dog running"
        assert inp.model is None

    def test_full_input(self):
        """Test creating VeoInput with all fields."""
        inp = VeoInput(
            provider="veo",
            model="veo-3.1-generate-001",
            prompt="A magical forest",
            input_image=ImageInput(url="https://example.com/forest.jpg"),
            negative_prompt="blurry, distorted",
            last_frame=ImageInput(url="https://example.com/end.jpg"),
            reference_images=[
                ImageInput(url="https://example.com/ref1.jpg"),
                ImageInput(url="https://example.com/ref2.jpg"),
            ],
            num_outputs=3,
        )
        assert inp.provider == "veo"
        assert inp.model == "veo-3.1-generate-001"
        assert inp.negative_prompt == "blurry, distorted"
        assert len(inp.reference_images) == 2
        assert inp.num_outputs == 3

    def test_valid_models(self):
        """Test all valid Veo models."""
        models = [
            # Gemini API (API key mode)
            "veo-3.1-generate-preview",
            # Vertex AI mode
            "veo-3.1-generate-001",
            "veo-3.1-fast-generate-001",
            "veo-3.1-fast-generate-preview",
        ]
        for model in models:
            inp = VeoInput(prompt="test", model=model)
            assert inp.model == model

    def test_num_outputs_range(self):
        """Test num_outputs validation (1-4)."""
        # Valid range
        for n in [1, 2, 3, 4]:
            inp = VeoInput(prompt="test", num_outputs=n)
            assert inp.num_outputs == n

        # Invalid: 0
        with pytest.raises(ValidationError):
            VeoInput(prompt="test", num_outputs=0)

        # Invalid: 5
        with pytest.raises(ValidationError):
            VeoInput(prompt="test", num_outputs=5)


class TestGenerationConfig:
    """Tests for GenerationConfig model."""

    def test_defaults(self):
        """Test default values."""
        config = GenerationConfig()
        assert config.duration == 8
        assert config.aspect_ratio == "9:16"  # Default is portrait
        assert config.resolution == "720p"

    def test_custom_values(self):
        """Test custom configuration."""
        config = GenerationConfig(
            duration=4,
            aspect_ratio="9:16",
        )
        assert config.duration == 4
        assert config.aspect_ratio == "9:16"
        assert config.resolution == "720p"  # Fixed value

    def test_valid_aspect_ratios(self):
        """Test valid aspect ratios."""
        for ar in ["16:9", "9:16"]:
            config = GenerationConfig(aspect_ratio=ar)
            assert config.aspect_ratio == ar

    def test_invalid_aspect_ratio(self):
        """Test invalid aspect ratio raises error."""
        with pytest.raises(ValidationError):
            GenerationConfig(aspect_ratio="4:3")


class TestGeneratedVideo:
    """Tests for GeneratedVideo model."""

    def test_minimal_video(self):
        """Test creating GeneratedVideo with required fields only."""
        video = GeneratedVideo(
            id="video_001",
            status="queued",
            created_at="2025-01-20T12:00:00Z",
        )
        assert video.id == "video_001"
        assert video.status == "queued"
        assert video.selected is False  # Default value

    def test_completed_video(self):
        """Test creating a completed GeneratedVideo."""
        video = GeneratedVideo(
            id="video_001",
            status="completed",
            progress=100,
            created_at="2025-01-20T12:00:00Z",
            video_url="https://api.example.com/videos/video_001/video.mp4",
            thumbnail_url="https://api.example.com/videos/video_001/thumb.jpg",
            duration=8,
            resolution="1280x720",
            has_audio=True,
            selected=True,
        )
        assert video.status == "completed"
        assert video.progress == 100
        assert video.video_url is not None
        assert video.selected is True

    def test_failed_video(self):
        """Test creating a failed GeneratedVideo."""
        video = GeneratedVideo(
            id="video_001",
            status="failed",
            created_at="2025-01-20T12:00:00Z",
            error="Content policy violation",
        )
        assert video.status == "failed"
        assert video.error == "Content policy violation"

    def test_valid_statuses(self):
        """Test all valid status values."""
        for status in ["queued", "in_progress", "completed", "failed"]:
            video = GeneratedVideo(
                id="video_001",
                status=status,
                created_at="2025-01-20T12:00:00Z",
            )
            assert video.status == status

    def test_progress_range(self):
        """Test progress validation (0-100)."""
        # Valid range
        for p in [0, 50, 100]:
            video = GeneratedVideo(
                id="video_001",
                status="in_progress",
                created_at="2025-01-20T12:00:00Z",
                progress=p,
            )
            assert video.progress == p

        # Invalid: negative
        with pytest.raises(ValidationError):
            GeneratedVideo(
                id="video_001",
                status="in_progress",
                created_at="2025-01-20T12:00:00Z",
                progress=-1,
            )

        # Invalid: over 100
        with pytest.raises(ValidationError):
            GeneratedVideo(
                id="video_001",
                status="in_progress",
                created_at="2025-01-20T12:00:00Z",
                progress=101,
            )


class TestGenerationResult:
    """Tests for GenerationResult model."""

    def test_creation(self):
        """Test creating GenerationResult."""
        result = GenerationResult(
            input_index=0,
            provider="sora",
            video=GeneratedVideo(
                id="video_001",
                status="completed",
                created_at="2025-01-20T12:00:00Z",
            ),
        )
        assert result.input_index == 0
        assert result.provider == "sora"
        assert result.video.id == "video_001"

    def test_valid_providers(self):
        """Test valid provider values."""
        for provider in ["sora", "veo"]:
            result = GenerationResult(
                input_index=0,
                provider=provider,
                video=GeneratedVideo(
                    id="video_001",
                    status="completed",
                    created_at="2025-01-20T12:00:00Z",
                ),
            )
            assert result.provider == provider

    def test_input_index_non_negative(self):
        """Test input_index must be non-negative."""
        with pytest.raises(ValidationError):
            GenerationResult(
                input_index=-1,
                provider="sora",
                video=GeneratedVideo(
                    id="video_001",
                    status="completed",
                    created_at="2025-01-20T12:00:00Z",
                ),
            )
