"""Video generation module with unified interface for Sora and Veo providers."""

from .exceptions import (
    InvalidConfigurationError,
    ProviderAuthenticationError,
    ProviderNotFoundError,
    VideoGenerationError,
    VideoGenerationRequestError,
    VideoGenerationTimeoutError,
    VideoNotFoundError,
)
from .providers import SoraProvider, VeoProvider, VideoProvider
from .service import VideoGenerationService
from .types import (
    GeneratedVideo,
    GenerationConfig,
    GenerationResult,
    ImageInput,
    SoraInput,
    VeoInput,
    VideoGenerationInput,
)

__all__ = [
    # Service
    "VideoGenerationService",
    # Providers
    "VideoProvider",
    "SoraProvider",
    "VeoProvider",
    # Types
    "ImageInput",
    "SoraInput",
    "VeoInput",
    "VideoGenerationInput",
    "GenerationConfig",
    "GeneratedVideo",
    "GenerationResult",
    # Exceptions
    "VideoGenerationError",
    "ProviderNotFoundError",
    "ProviderAuthenticationError",
    "VideoGenerationRequestError",
    "VideoNotFoundError",
    "VideoGenerationTimeoutError",
    "InvalidConfigurationError",
]
