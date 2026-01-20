"""Tests for VideoGenerationService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.integrations.video_generation import (
    GeneratedVideo,
    GenerationConfig,
    SoraInput,
    VeoInput,
    VideoGenerationService,
)
from app.integrations.video_generation.exceptions import ProviderNotFoundError


class TestVideoGenerationService:
    """Tests for VideoGenerationService."""

    def test_init_default(self, mock_all_api_keys):
        """Test default initialization."""
        service = VideoGenerationService()
        assert service._providers == {}

    def test_init_with_keys(self):
        """Test initialization with explicit API keys."""
        service = VideoGenerationService(
            sora_api_key="sk-test",
            google_api_key="google-test",
        )
        assert service._sora_api_key == "sk-test"
        assert service._google_api_key == "google-test"

    @pytest.mark.asyncio
    async def test_generate_routes_to_sora(self, mock_all_api_keys):
        """Test that SoraInput routes to SoraProvider."""
        service = VideoGenerationService()

        mock_video = GeneratedVideo(
            id="video_sora_001",
            status="queued",
            created_at="2025-01-20T12:00:00Z",
        )

        with patch(
            "app.integrations.video_generation.service.SoraProvider"
        ) as mock_provider_class:
            mock_provider = MagicMock()
            mock_provider.generate = AsyncMock(return_value=mock_video)
            mock_provider_class.return_value = mock_provider

            result = await service.generate(
                SoraInput(prompt="A cat walking"),
                GenerationConfig(),
            )

            assert result.id == "video_sora_001"
            mock_provider.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_routes_to_veo(self, mock_all_api_keys):
        """Test that VeoInput routes to VeoProvider."""
        service = VideoGenerationService()

        mock_video = GeneratedVideo(
            id="video_veo_001",
            status="in_progress",
            created_at="2025-01-20T12:00:00Z",
            has_audio=True,
        )

        with patch(
            "app.integrations.video_generation.service.VeoProvider"
        ) as mock_provider_class:
            mock_provider = MagicMock()
            mock_provider.generate = AsyncMock(return_value=mock_video)
            mock_provider_class.return_value = mock_provider

            result = await service.generate(
                VeoInput(prompt="A dog running"),
                GenerationConfig(),
            )

            assert result.id == "video_veo_001"
            assert result.has_audio is True
            mock_provider.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_uses_default_config(self, mock_all_api_keys):
        """Test that default config is used when not provided."""
        service = VideoGenerationService()

        mock_video = GeneratedVideo(
            id="video_001",
            status="queued",
            created_at="2025-01-20T12:00:00Z",
        )

        with patch(
            "app.integrations.video_generation.service.SoraProvider"
        ) as mock_provider_class:
            mock_provider = MagicMock()
            mock_provider.generate = AsyncMock(return_value=mock_video)
            mock_provider_class.return_value = mock_provider

            await service.generate(SoraInput(prompt="Test"))

            # Verify generate was called with a GenerationConfig
            call_args = mock_provider.generate.call_args
            assert isinstance(call_args[0][1], GenerationConfig)

    @pytest.mark.asyncio
    async def test_generate_batch(self, mock_all_api_keys):
        """Test batch generation with multiple inputs."""
        service = VideoGenerationService()

        mock_sora_video = GeneratedVideo(
            id="video_sora_001",
            status="queued",
            created_at="2025-01-20T12:00:00Z",
        )
        mock_veo_video = GeneratedVideo(
            id="video_veo_001",
            status="in_progress",
            created_at="2025-01-20T12:00:00Z",
        )

        with patch(
            "app.integrations.video_generation.service.SoraProvider"
        ) as mock_sora_class, patch(
            "app.integrations.video_generation.service.VeoProvider"
        ) as mock_veo_class:
            mock_sora = MagicMock()
            mock_sora.generate = AsyncMock(return_value=mock_sora_video)
            mock_sora_class.return_value = mock_sora

            mock_veo = MagicMock()
            mock_veo.generate = AsyncMock(return_value=mock_veo_video)
            mock_veo_class.return_value = mock_veo

            inputs = [
                (SoraInput(prompt="Cat walking"), 0),
                (VeoInput(prompt="Dog running"), 1),
            ]

            results = await service.generate_batch(inputs, GenerationConfig())

            assert len(results) == 2
            assert results[0].input_index == 0
            assert results[0].provider == "sora"
            assert results[1].input_index == 1
            assert results[1].provider == "veo"

    @pytest.mark.asyncio
    async def test_get_status_sora(self, mock_all_api_keys):
        """Test getting status for Sora video."""
        service = VideoGenerationService()

        mock_video = GeneratedVideo(
            id="video_sora_001",
            status="in_progress",
            progress=50,
            created_at="2025-01-20T12:00:00Z",
        )

        with patch(
            "app.integrations.video_generation.service.SoraProvider"
        ) as mock_provider_class:
            mock_provider = MagicMock()
            mock_provider.get_status = AsyncMock(return_value=mock_video)
            mock_provider_class.return_value = mock_provider

            result = await service.get_status("sora", "video_sora_001")

            assert result.id == "video_sora_001"
            assert result.progress == 50
            mock_provider.get_status.assert_called_once_with("video_sora_001")

    @pytest.mark.asyncio
    async def test_get_status_veo(self, mock_all_api_keys):
        """Test getting status for Veo video."""
        service = VideoGenerationService()

        mock_video = GeneratedVideo(
            id="video_veo_001",
            status="completed",
            created_at="2025-01-20T12:00:00Z",
            video_url="https://storage.googleapis.com/video.mp4",
        )

        with patch(
            "app.integrations.video_generation.service.VeoProvider"
        ) as mock_provider_class:
            mock_provider = MagicMock()
            mock_provider.get_status = AsyncMock(return_value=mock_video)
            mock_provider_class.return_value = mock_provider

            result = await service.get_status("veo", "video_veo_001")

            assert result.id == "video_veo_001"
            assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_wait_for_completion(self, mock_all_api_keys):
        """Test waiting for video completion."""
        service = VideoGenerationService()

        mock_video = GeneratedVideo(
            id="video_001",
            status="completed",
            progress=100,
            created_at="2025-01-20T12:00:00Z",
            video_url="https://api.example.com/video.mp4",
        )

        with patch(
            "app.integrations.video_generation.service.SoraProvider"
        ) as mock_provider_class:
            mock_provider = MagicMock()
            mock_provider.wait_for_completion = AsyncMock(return_value=mock_video)
            mock_provider_class.return_value = mock_provider

            result = await service.wait_for_completion(
                "sora", "video_001", poll_interval=1.0, timeout=60.0
            )

            assert result.status == "completed"
            mock_provider.wait_for_completion.assert_called_once_with(
                "video_001", 1.0, 60.0
            )

    @pytest.mark.asyncio
    async def test_wait_for_batch(self, mock_all_api_keys):
        """Test waiting for multiple videos to complete."""
        service = VideoGenerationService()

        mock_sora_video = GeneratedVideo(
            id="video_sora_001",
            status="completed",
            created_at="2025-01-20T12:00:00Z",
        )
        mock_veo_video = GeneratedVideo(
            id="video_veo_001",
            status="completed",
            created_at="2025-01-20T12:00:00Z",
        )

        with patch(
            "app.integrations.video_generation.service.SoraProvider"
        ) as mock_sora_class, patch(
            "app.integrations.video_generation.service.VeoProvider"
        ) as mock_veo_class:
            mock_sora = MagicMock()
            mock_sora.wait_for_completion = AsyncMock(return_value=mock_sora_video)
            mock_sora_class.return_value = mock_sora

            mock_veo = MagicMock()
            mock_veo.wait_for_completion = AsyncMock(return_value=mock_veo_video)
            mock_veo_class.return_value = mock_veo

            videos = [
                ("sora", "video_sora_001", 0),
                ("veo", "video_veo_001", 1),
            ]

            results = await service.wait_for_batch(videos)

            assert len(results) == 2
            assert all(r.video.status == "completed" for r in results)

    @pytest.mark.asyncio
    async def test_get_video_url(self, mock_all_api_keys):
        """Test getting video download URL."""
        service = VideoGenerationService()

        with patch(
            "app.integrations.video_generation.service.SoraProvider"
        ) as mock_provider_class:
            mock_provider = MagicMock()
            mock_provider.get_video_url = AsyncMock(
                return_value="https://api.example.com/video.mp4"
            )
            mock_provider_class.return_value = mock_provider

            url = await service.get_video_url("sora", "video_001")

            assert url == "https://api.example.com/video.mp4"

    def test_provider_reuse(self, mock_all_api_keys):
        """Test that providers are reused across calls."""
        with patch(
            "app.integrations.video_generation.service.SoraProvider"
        ) as mock_provider_class:
            mock_provider = MagicMock()
            mock_provider_class.return_value = mock_provider

            service = VideoGenerationService()

            # Get provider twice
            provider1 = service._get_provider("sora")
            provider2 = service._get_provider("sora")

            # Should be the same instance
            assert provider1 is provider2
            # Provider class should only be instantiated once
            assert mock_provider_class.call_count == 1
