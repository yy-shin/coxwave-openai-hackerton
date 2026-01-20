"""Custom exceptions for video generation module."""


class VideoGenerationError(Exception):
    """Base exception for video generation errors."""

    def __init__(self, message: str, provider: str | None = None):
        self.message = message
        self.provider = provider
        super().__init__(message)


class ProviderNotFoundError(VideoGenerationError):
    """Raised when an unknown provider is requested."""

    def __init__(self, provider: str):
        super().__init__(f"Unknown video provider: {provider}", provider)


class ProviderAuthenticationError(VideoGenerationError):
    """Raised when provider authentication fails."""

    def __init__(self, provider: str, details: str | None = None):
        message = f"Authentication failed for {provider}"
        if details:
            message += f": {details}"
        super().__init__(message, provider)


class VideoGenerationRequestError(VideoGenerationError):
    """Raised when a video generation request fails."""

    def __init__(self, provider: str, status_code: int | None = None, details: str | None = None):
        message = f"Video generation request failed for {provider}"
        if status_code:
            message += f" (status {status_code})"
        if details:
            message += f": {details}"
        self.status_code = status_code
        super().__init__(message, provider)


class VideoNotFoundError(VideoGenerationError):
    """Raised when a video ID is not found."""

    def __init__(self, provider: str, video_id: str):
        self.video_id = video_id
        super().__init__(f"Video not found: {video_id} (provider: {provider})", provider)


class VideoGenerationTimeoutError(VideoGenerationError):
    """Raised when video generation times out."""

    def __init__(self, provider: str, video_id: str, timeout_seconds: float):
        self.video_id = video_id
        self.timeout_seconds = timeout_seconds
        super().__init__(
            f"Video generation timed out after {timeout_seconds}s: {video_id} (provider: {provider})",
            provider,
        )


class InvalidConfigurationError(VideoGenerationError):
    """Raised when configuration is invalid for a provider."""

    def __init__(self, provider: str, details: str):
        super().__init__(f"Invalid configuration for {provider}: {details}", provider)
