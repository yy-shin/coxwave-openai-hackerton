"""Tests for video generation providers (Sora, Veo)."""

import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.video_generation import GenerationConfig, SoraInput, VeoInput
from app.integrations.video_generation.exceptions import (
    InvalidConfigurationError,
    ProviderAuthenticationError,
    VideoGenerationRequestError,
    VideoNotFoundError,
)
from app.integrations.video_generation.providers.sora import SoraProvider
from app.integrations.video_generation.providers.veo import VeoProvider


class TestSoraProvider:
    """Tests for SoraProvider."""

    def test_init_with_api_key(self):
        """Test initialization with explicit API key."""
        provider = SoraProvider(api_key="sk-test-key")
        assert provider.api_key == "sk-test-key"
        assert provider.provider_name == "sora"

    def test_init_from_env(self, mock_openai_api_key):
        """Test initialization from environment variable."""
        provider = SoraProvider()
        assert provider.api_key == "sk-test-key-12345"

    def test_init_missing_key(self):
        """Test initialization fails without API key."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove OPENAI_API_KEY if it exists
            os.environ.pop("OPENAI_API_KEY", None)
            with pytest.raises(ProviderAuthenticationError) as exc_info:
                SoraProvider()
            assert "OPENAI_API_KEY" in str(exc_info.value)

    def test_get_size_landscape(self, mock_openai_api_key):
        """Test size mapping for landscape aspect ratio."""
        provider = SoraProvider()
        config = GenerationConfig(aspect_ratio="16:9", resolution="720p")
        assert provider._get_size(config) == "1280x720"

    def test_get_size_portrait(self, mock_openai_api_key):
        """Test size mapping for portrait aspect ratio."""
        provider = SoraProvider()
        config = GenerationConfig(aspect_ratio="9:16", resolution="720p")
        assert provider._get_size(config) == "720x1280"

    def test_validate_duration_supported(self, mock_openai_api_key):
        """Test duration validation for supported values."""
        provider = SoraProvider()
        assert provider._validate_duration(4) == 4
        assert provider._validate_duration(8) == 8
        assert provider._validate_duration(12) == 12

    def test_validate_duration_unsupported(self, mock_openai_api_key):
        """Test duration validation rounds to closest supported value."""
        provider = SoraProvider()
        # 6 is not supported by Sora, should round to closest (4 or 8)
        result = provider._validate_duration(6)
        assert result in [4, 8]

    def test_parse_video_response_queued(self, mock_openai_api_key, mock_sora_queued_response):
        """Test parsing queued response."""
        provider = SoraProvider()
        video = provider._parse_video_response(mock_sora_queued_response)

        assert video.id == "video_sora_test_001"
        assert video.status == "queued"
        assert video.video_url is None
        assert video.has_audio is False

    def test_parse_video_response_completed(self, mock_openai_api_key, mock_sora_completed_response):
        """Test parsing completed response."""
        provider = SoraProvider()
        video = provider._parse_video_response(mock_sora_completed_response)

        assert video.id == "video_sora_test_001"
        assert video.status == "completed"
        assert video.video_url is not None
        assert "video_sora_test_001" in video.video_url

    def test_parse_video_response_failed(self, mock_openai_api_key, mock_sora_failed_response):
        """Test parsing failed response."""
        provider = SoraProvider()
        video = provider._parse_video_response(mock_sora_failed_response)

        assert video.id == "video_sora_test_001"
        assert video.status == "failed"
        assert video.error == "Content policy violation"

    @pytest.mark.asyncio
    async def test_generate_success(self, mock_openai_api_key, sample_sora_input, default_config):
        """Test successful video generation."""
        provider = SoraProvider()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "video_test_001",
            "status": "queued",
            "created_at": 1705776000,
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await provider.generate(sample_sora_input, default_config)

            assert result.id == "video_test_001"
            assert result.status == "queued"

    @pytest.mark.asyncio
    async def test_generate_auth_error(self, mock_openai_api_key, sample_sora_input, default_config):
        """Test authentication error handling."""
        provider = SoraProvider()

        mock_response = MagicMock()
        mock_response.status_code = 401

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            with pytest.raises(ProviderAuthenticationError):
                await provider.generate(sample_sora_input, default_config)

    @pytest.mark.asyncio
    async def test_get_status_success(self, mock_openai_api_key):
        """Test getting video status."""
        provider = SoraProvider()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "video_test_001",
            "status": "in_progress",
            "progress": 50,
            "created_at": 1705776000,
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await provider.get_status("video_test_001")

            assert result.id == "video_test_001"
            assert result.status == "in_progress"
            assert result.progress == 50

    @pytest.mark.asyncio
    async def test_get_status_not_found(self, mock_openai_api_key):
        """Test video not found error."""
        provider = SoraProvider()

        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            with pytest.raises(VideoNotFoundError):
                await provider.get_status("nonexistent_video")


class TestVeoProvider:
    """Tests for VeoProvider."""

    def test_init_with_api_key(self):
        """Test initialization with explicit API key."""
        with patch("app.integrations.video_generation.providers.veo.genai.Client") as mock_client:
            provider = VeoProvider(api_key="google-test-key")
            assert provider.api_key == "google-test-key"
            assert provider.provider_name == "veo"
            mock_client.assert_called_once()

    def test_init_from_env(self, mock_google_api_key):
        """Test initialization from environment variable."""
        with patch("app.integrations.video_generation.providers.veo.genai.Client"):
            provider = VeoProvider()
            assert provider.api_key == "google-test-key-12345"

    def test_init_missing_credentials(self):
        """Test initialization fails without credentials."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("GOOGLE_API_KEY", None)
            os.environ.pop("GOOGLE_CLOUD_PROJECT", None)
            with pytest.raises(ProviderAuthenticationError) as exc_info:
                VeoProvider()
            assert "GOOGLE_API_KEY" in str(exc_info.value)

    def test_validate_duration_supported(self, mock_google_api_key):
        """Test duration validation for supported values."""
        with patch("app.integrations.video_generation.providers.veo.genai.Client"):
            provider = VeoProvider()
            assert provider._validate_duration(4) == 4
            assert provider._validate_duration(6) == 6
            assert provider._validate_duration(8) == 8

    def test_validate_duration_unsupported(self, mock_google_api_key):
        """Test duration validation rounds to closest supported value."""
        with patch("app.integrations.video_generation.providers.veo.genai.Client"):
            provider = VeoProvider()
            # 12 is not supported by Veo, should round to closest (8)
            result = provider._validate_duration(12)
            assert result == 8

    @pytest.mark.asyncio
    async def test_generate_success(self, mock_google_api_key, sample_veo_input, default_config):
        """Test successful video generation."""
        with patch("app.integrations.video_generation.providers.veo.genai.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_operation = MagicMock()
            mock_operation.name = "operations/veo_test_001"
            mock_client.models.generate_videos.return_value = mock_operation
            mock_client_class.return_value = mock_client

            provider = VeoProvider()
            result = await provider.generate(sample_veo_input, default_config)

            assert result.id == "operations/veo_test_001"
            assert result.status == "in_progress"
            assert result.has_audio is True

    @pytest.mark.asyncio
    async def test_generate_with_options(
        self, mock_google_api_key, sample_veo_input_with_options, default_config
    ):
        """Test video generation with all optional fields."""
        with patch("app.integrations.video_generation.providers.veo.genai.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_operation = MagicMock()
            mock_operation.name = "operations/veo_test_002"
            mock_client.models.generate_videos.return_value = mock_operation
            mock_client_class.return_value = mock_client

            provider = VeoProvider()
            result = await provider.generate(sample_veo_input_with_options, default_config)

            assert result.id == "operations/veo_test_002"
            # Verify generate_videos was called
            mock_client.models.generate_videos.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_status_completed(self, mock_google_api_key):
        """Test getting status of completed video."""
        with patch("app.integrations.video_generation.providers.veo.genai.Client") as mock_client_class:
            mock_client = MagicMock()

            # Mock completed operation
            mock_operation = MagicMock()
            mock_operation.done = True
            mock_operation.error = None
            mock_video = MagicMock()
            mock_video.uri = "https://storage.googleapis.com/video.mp4"
            mock_gen_video = MagicMock()
            mock_gen_video.video = mock_video
            mock_operation.response = MagicMock()
            mock_operation.response.generated_videos = [mock_gen_video]

            mock_client.operations.get.return_value = mock_operation
            mock_client_class.return_value = mock_client

            provider = VeoProvider()
            # Store the operation to simulate previous generate call
            provider._operations["operations/veo_test_001"] = datetime.now(
                tz=timezone.utc
            ).isoformat()

            result = await provider.get_status("operations/veo_test_001")

            assert result.status == "completed"
            assert result.video_url == "https://storage.googleapis.com/video.mp4"

    @pytest.mark.asyncio
    async def test_get_status_in_progress(self, mock_google_api_key):
        """Test getting status of in-progress video."""
        with patch("app.integrations.video_generation.providers.veo.genai.Client") as mock_client_class:
            mock_client = MagicMock()

            # Mock in-progress operation
            mock_operation = MagicMock()
            mock_operation.done = False

            mock_client.operations.get.return_value = mock_operation
            mock_client_class.return_value = mock_client

            provider = VeoProvider()
            result = await provider.get_status("operations/veo_test_001")

            assert result.status == "in_progress"

    @pytest.mark.asyncio
    async def test_get_status_failed(self, mock_google_api_key):
        """Test getting status of failed video."""
        with patch("app.integrations.video_generation.providers.veo.genai.Client") as mock_client_class:
            mock_client = MagicMock()

            # Mock failed operation
            mock_operation = MagicMock()
            mock_operation.done = True
            mock_operation.error = MagicMock()
            mock_operation.error.__str__ = lambda self: "Generation failed"

            mock_client.operations.get.return_value = mock_operation
            mock_client_class.return_value = mock_client

            provider = VeoProvider()
            result = await provider.get_status("operations/veo_test_001")

            assert result.status == "failed"
            assert result.error is not None
