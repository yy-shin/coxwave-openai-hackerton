"""Pytest configuration and shared fixtures for video generation tests."""

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from dotenv import load_dotenv

# Load environment variables from backend/.env
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

from app.integrations.video_generation import (
    GeneratedVideo,
    GenerationConfig,
    ImageInput,
    SoraInput,
    VeoInput,
)


# Configure pytest-asyncio
pytest_plugins = ("pytest_asyncio",)


@pytest.fixture
def test_output_dir() -> Path:
    """Create and return the test outputs directory."""
    output_dir = Path(__file__).parent.parent / "test_outputs"
    output_dir.mkdir(exist_ok=True)
    return output_dir


# ============================================================================
# Input Fixtures
# ============================================================================


@pytest.fixture
def sample_sora_input() -> SoraInput:
    """Create a sample Sora input for testing."""
    return SoraInput(
        provider="sora",
        model="sora-2",
        prompt="A cute cat walking through a sunny garden, cinematic lighting",
    )


@pytest.fixture
def sample_sora_input_with_image() -> SoraInput:
    """Create a Sora input with an input image."""
    return SoraInput(
        provider="sora",
        model="sora-2",
        prompt="Transform this image into a video with gentle movement",
        input_image=ImageInput(
            url="https://example.com/sample_image.jpg",
        ),
    )


@pytest.fixture
def sample_veo_input() -> VeoInput:
    """Create a sample Veo input for testing."""
    return VeoInput(
        provider="veo",
        model="veo-3.1-generate-preview",  # Works with API key mode
        prompt="A dog running happily on a beach at sunset, golden hour lighting",
    )


@pytest.fixture
def sample_veo_input_with_options() -> VeoInput:
    """Create a Veo input with all optional fields.

    Note: Veo requires GCS URIs (gs://...) or base64-encoded images.
    Using GCS URIs for test fixtures.
    """
    return VeoInput(
        provider="veo",
        model="veo-3.1-generate-preview",  # Works with API key mode
        prompt="A magical forest with glowing fireflies",
        negative_prompt="blurry, low quality, distorted",
        input_image=ImageInput(url="gs://example-bucket/forest.jpg"),
        reference_images=[
            ImageInput(url="gs://example-bucket/style_ref1.jpg"),
            ImageInput(url="gs://example-bucket/style_ref2.jpg"),
        ],
        num_outputs=2,
    )


@pytest.fixture
def sample_image_input_url() -> ImageInput:
    """Create an ImageInput with URL."""
    return ImageInput(url="https://example.com/image.png")


@pytest.fixture
def sample_image_input_base64() -> ImageInput:
    """Create an ImageInput with base64 data."""
    return ImageInput(
        base64="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        mime_type="image/png",
    )


# ============================================================================
# Config Fixtures
# ============================================================================


@pytest.fixture
def default_config() -> GenerationConfig:
    """Create default generation config."""
    return GenerationConfig()


@pytest.fixture
def landscape_config() -> GenerationConfig:
    """Create landscape 16:9 config."""
    return GenerationConfig(
        duration=8,
        aspect_ratio="16:9",
        resolution="720p",
    )


@pytest.fixture
def portrait_config() -> GenerationConfig:
    """Create portrait 9:16 config."""
    return GenerationConfig(
        duration=8,
        aspect_ratio="9:16",
        resolution="720p",
    )


@pytest.fixture
def short_duration_config() -> GenerationConfig:
    """Create short duration config."""
    return GenerationConfig(duration=4, aspect_ratio="16:9")


@pytest.fixture
def long_duration_config() -> GenerationConfig:
    """Create long duration config (12s - Sora only)."""
    return GenerationConfig(duration=12, aspect_ratio="16:9")


# ============================================================================
# Output Fixtures (Mock Responses)
# ============================================================================


@pytest.fixture
def mock_sora_queued_response() -> dict:
    """Mock Sora API response for a queued video."""
    return {
        "id": "video_sora_test_001",
        "status": "queued",
        "created_at": 1705776000,
        "model": "sora-2",
        "size": "1280x720",
        "seconds": 8,
    }


@pytest.fixture
def mock_sora_in_progress_response() -> dict:
    """Mock Sora API response for an in-progress video."""
    return {
        "id": "video_sora_test_001",
        "status": "in_progress",
        "progress": 45,
        "created_at": 1705776000,
        "model": "sora-2",
        "size": "1280x720",
        "seconds": 8,
    }


@pytest.fixture
def mock_sora_completed_response() -> dict:
    """Mock Sora API response for a completed video."""
    return {
        "id": "video_sora_test_001",
        "status": "completed",
        "progress": 100,
        "created_at": 1705776000,
        "model": "sora-2",
        "size": "1280x720",
        "seconds": 8,
    }


@pytest.fixture
def mock_sora_failed_response() -> dict:
    """Mock Sora API response for a failed video."""
    return {
        "id": "video_sora_test_001",
        "status": "failed",
        "created_at": 1705776000,
        "failure_reason": "Content policy violation",
    }


@pytest.fixture
def mock_generated_video_completed() -> GeneratedVideo:
    """Create a mock completed GeneratedVideo."""
    return GeneratedVideo(
        id="video_test_001",
        status="completed",
        progress=100,
        created_at="2025-01-20T12:00:00Z",
        video_url="https://api.example.com/videos/video_test_001/content/video.mp4",
        duration=8,
        resolution="1280x720",
        has_audio=False,
    )


@pytest.fixture
def mock_generated_video_in_progress() -> GeneratedVideo:
    """Create a mock in-progress GeneratedVideo."""
    return GeneratedVideo(
        id="video_test_002",
        status="in_progress",
        progress=50,
        created_at="2025-01-20T12:00:00Z",
    )


@pytest.fixture
def mock_generated_video_failed() -> GeneratedVideo:
    """Create a mock failed GeneratedVideo."""
    return GeneratedVideo(
        id="video_test_003",
        status="failed",
        created_at="2025-01-20T12:00:00Z",
        error="Generation failed: content policy violation",
    )


# ============================================================================
# Environment Fixtures
# ============================================================================


@pytest.fixture
def mock_openai_api_key():
    """Mock OPENAI_API_KEY environment variable."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key-12345"}):
        yield "sk-test-key-12345"


@pytest.fixture
def mock_google_api_key():
    """Mock GOOGLE_API_KEY environment variable."""
    with patch.dict(os.environ, {"GOOGLE_API_KEY": "google-test-key-12345"}):
        yield "google-test-key-12345"


@pytest.fixture
def mock_all_api_keys():
    """Mock all API keys."""
    keys = {
        "OPENAI_API_KEY": "sk-test-key-12345",
        "GOOGLE_API_KEY": "google-test-key-12345",
    }
    with patch.dict(os.environ, keys):
        yield keys


# ============================================================================
# Provider Mock Fixtures
# ============================================================================


@pytest.fixture
def mock_httpx_client():
    """Create a mock httpx.AsyncClient for Sora tests."""
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


@pytest.fixture
def mock_genai_client():
    """Create a mock google.genai.Client for Veo tests."""
    mock_client = MagicMock()
    mock_client.models = MagicMock()
    mock_client.operations = MagicMock()
    return mock_client
