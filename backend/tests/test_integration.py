"""
Integration tests for video generation with real API calls.

These tests require actual API keys and will incur costs.
Run with: pytest tests/test_integration.py -v -s

Set environment variables:
- OPENAI_API_KEY: For Sora tests
- GOOGLE_API_KEY: For Veo tests

Skip with: pytest tests/test_integration.py -v -s -k "not integration"
"""

import asyncio
import base64
import io
import json
import mimetypes
import os
from datetime import datetime
from pathlib import Path

import httpx
import pytest
from PIL import Image

from app.integrations.video_generation import (
    GeneratedVideo,
    GenerationConfig,
    ImageInput,
    SoraInput,
    VeoInput,
    VideoGenerationService,
)


# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


def get_data_images_dir() -> Path:
    """Get the data/images directory."""
    return Path(__file__).parent.parent.parent / "data" / "images"


def load_image_as_base64(
    image_path: Path,
    target_size: tuple[int, int] | None = None,
) -> ImageInput:
    """Load an image file and return as ImageInput with base64 encoding.

    Args:
        image_path: Path to the image file
        target_size: Optional (width, height) to resize the image to.
                    Required for Sora which needs exact dimensions.
    """
    # Load image with PIL
    img = Image.open(image_path)

    # Resize if target size is specified
    if target_size:
        # Use LANCZOS for high quality resize
        img = img.resize(target_size, Image.Resampling.LANCZOS)

    # Convert to RGB if necessary (remove alpha channel)
    if img.mode in ("RGBA", "LA", "P"):
        # Create white background
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
        img = background

    # Save to bytes buffer as PNG
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    image_bytes = buffer.getvalue()

    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    return ImageInput(base64=image_base64, mime_type="image/png")


def get_output_dir() -> Path:
    """Get or create the video output directory."""
    output_dir = Path(__file__).parent.parent.parent / "data" / "videos"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def save_result(name: str, result: GeneratedVideo, output_dir: Path) -> None:
    """Save generation result to JSON file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{name}_{timestamp}.json"
    filepath = output_dir / filename

    data = result.model_dump()
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nResult saved to: {filepath}")


async def download_video(url: str, filepath: Path, api_key: str | None = None) -> None:
    """Download video from URL to file."""
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, follow_redirects=True, timeout=120.0)
        response.raise_for_status()

        with open(filepath, "wb") as f:
            f.write(response.content)

    print(f"Video downloaded to: {filepath}")


@pytest.fixture
def output_dir() -> Path:
    """Provide output directory for tests."""
    return get_output_dir()


@pytest.fixture
def data_images_dir() -> Path:
    """Provide data images directory for tests."""
    return get_data_images_dir()


@pytest.fixture
def sample_image(data_images_dir) -> ImageInput | None:
    """Load sample image from data/images as base64 (original size)."""
    image_path = data_images_dir / "image2_square.png"
    if image_path.exists():
        return load_image_as_base64(image_path)
    return None


@pytest.fixture
def sample_image_720p_landscape(data_images_dir) -> ImageInput | None:
    """Load sample image resized to 1280x720 (16:9) for Sora."""
    image_path = data_images_dir / "image2_square.png"
    if image_path.exists():
        return load_image_as_base64(image_path, target_size=(1280, 720))
    return None


@pytest.fixture
def sample_image_720p_portrait(data_images_dir) -> ImageInput | None:
    """Load sample image resized to 720x1280 (9:16) for Sora."""
    image_path = data_images_dir / "image2_square.png"
    if image_path.exists():
        return load_image_as_base64(image_path, target_size=(720, 1280))
    return None


@pytest.fixture
def service() -> VideoGenerationService:
    """Create VideoGenerationService instance."""
    return VideoGenerationService()


class TestSoraIntegration:
    """Integration tests for Sora provider."""

    @pytest.fixture(autouse=True)
    def skip_if_no_key(self):
        """Skip tests if OPENAI_API_KEY is not set."""
        if not os.environ.get("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY not set")

    @pytest.mark.asyncio
    async def test_sora_generate_and_poll(self, service, output_dir):
        """Test Sora video generation with polling until completion."""
        config = GenerationConfig(
            duration=4,  # Shortest duration for faster test
            aspect_ratio="16:9",
        )

        input_data = SoraInput(
            prompt="A cute orange cat walking slowly through a sunny garden, cinematic quality",
            model="sora-2",
        )

        print("\n=== Starting Sora Generation ===")
        print(f"Prompt: {input_data.prompt}")
        print(f"Duration: {config.duration}s")

        # Start generation
        result = await service.generate(input_data, config)
        print(f"Video ID: {result.id}")
        print(f"Initial status: {result.status}")

        # Save initial result
        save_result("sora_initial", result, output_dir)

        # Poll until completion (with timeout)
        print("\nPolling for completion...")
        final_result = await service.wait_for_completion(
            "sora",
            result.id,
            poll_interval=10.0,
            timeout=600.0,  # 10 minutes
        )

        print(f"Final status: {final_result.status}")
        if final_result.error:
            print(f"Error: {final_result.error}")

        # Save final result
        save_result("sora_final", final_result, output_dir)

        # Download video if completed
        if final_result.status == "completed" and final_result.video_url:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            video_path = output_dir / f"sora_video_{timestamp}.mp4"
            await download_video(
                final_result.video_url,
                video_path,
                api_key=os.environ.get("OPENAI_API_KEY"),
            )

        assert final_result.status in ["completed", "failed"]

    @pytest.mark.asyncio
    async def test_sora_generate_only(self, service, output_dir):
        """Test Sora video generation without waiting for completion."""
        config = GenerationConfig(duration=4, aspect_ratio="16:9")

        input_data = SoraInput(
            prompt="A golden retriever puppy playing with a ball in a park",
            model="sora-2",
        )

        print("\n=== Starting Sora Generation (no wait) ===")
        result = await service.generate(input_data, config)

        print(f"Video ID: {result.id}")
        print(f"Status: {result.status}")

        save_result("sora_nowait", result, output_dir)

        assert result.id is not None
        assert result.status in ["queued", "in_progress"]

    @pytest.mark.asyncio
    async def test_sora_with_base64_image(self, service, output_dir, sample_image_720p_landscape):
        """Test Sora video generation with base64 image input.

        Note: Sora requires the input image to match the video dimensions exactly.
        For 16:9 at 720p, the image must be 1280x720.
        """
        if sample_image_720p_landscape is None:
            pytest.skip("No sample image found in data/images")

        config = GenerationConfig(
            duration=4,
            aspect_ratio="16:9",
        )

        input_data = SoraInput(
            prompt="Animate this image with gentle movement, the character slowly turns their head and smiles",
            model="sora-2",
            input_image=sample_image_720p_landscape,
        )

        print("\n=== Starting Sora Generation with Base64 Image ===")
        print(f"Prompt: {input_data.prompt}")
        print(f"Image mime_type: {sample_image_720p_landscape.mime_type}")
        print(f"Image base64 length: {len(sample_image_720p_landscape.base64)} chars")
        print(f"Image resized to: 1280x720 (matching 16:9 720p)")

        result = await service.generate(input_data, config)

        print(f"Video ID: {result.id}")
        print(f"Status: {result.status}")

        save_result("sora_with_image", result, output_dir)

        assert result.id is not None
        assert result.status in ["queued", "in_progress"]


class TestVeoIntegration:
    """Integration tests for Veo provider."""

    @pytest.fixture(autouse=True)
    def skip_if_no_key(self):
        """Skip tests if GOOGLE_API_KEY is not set."""
        if not os.environ.get("GOOGLE_API_KEY"):
            pytest.skip("GOOGLE_API_KEY not set")

    @pytest.mark.asyncio
    async def test_veo_generate_and_poll(self, service, output_dir):
        """Test Veo video generation with polling until completion."""
        config = GenerationConfig(
            duration=4,  # Shortest duration for faster test
            aspect_ratio="9:16",
        )

        input_data = VeoInput(
            prompt="A beautiful sunset over the ocean with gentle waves, cinematic 4K quality",
            model="veo-3.1-generate-preview",  # Use preview model (works with API key)
            negative_prompt="blurry, low quality, distorted",
        )

        print("\n=== Starting Veo Generation ===")
        print(f"Prompt: {input_data.prompt}")
        print(f"Duration: {config.duration}s")

        # Start generation
        result = await service.generate(input_data, config)
        print(f"Video ID: {result.id}")
        print(f"Initial status: {result.status}")

        # Save initial result
        save_result("veo_initial", result, output_dir)

        # Poll until completion (with timeout)
        print("\nPolling for completion...")
        final_result = await service.wait_for_completion(
            "veo",
            result.id,
            poll_interval=10.0,
            timeout=600.0,  # 10 minutes
        )

        print(f"Final status: {final_result.status}")
        if final_result.error:
            print(f"Error: {final_result.error}")

        # Save final result
        save_result("veo_final", final_result, output_dir)

        # Download video if completed
        if final_result.status == "completed" and final_result.video_url:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            video_path = output_dir / f"veo_video_{timestamp}.mp4"
            await download_video(final_result.video_url, video_path)

        assert final_result.status in ["completed", "failed"]

    @pytest.mark.asyncio
    async def test_veo_generate_only(self, service, output_dir):
        """Test Veo video generation without waiting for completion."""
        config = GenerationConfig(duration=4, aspect_ratio="9:16")

        input_data = VeoInput(
            prompt="A colorful butterfly landing on a flower in slow motion",
            model="veo-3.1-generate-preview",  # Use preview model (works with API key)
        )

        print("\n=== Starting Veo Generation (no wait) ===")
        result = await service.generate(input_data, config)

        print(f"Video ID: {result.id}")
        print(f"Status: {result.status}")

        save_result("veo_nowait", result, output_dir)

        assert result.id is not None
        assert result.status in ["queued", "in_progress"]

    @pytest.mark.asyncio
    async def test_veo_with_base64_image(self, service, output_dir, sample_image):
        """Test Veo video generation with base64 image input."""
        if sample_image is None:
            pytest.skip("No sample image found in data/images")

        config = GenerationConfig(
            duration=4,
            aspect_ratio="9:16",
        )

        input_data = VeoInput(
            prompt="Animate this image with cinematic camera movement, slow zoom in with ambient lighting",
            model="veo-3.1-generate-preview",  # Use preview model (works with API key)
            input_image=sample_image,
            negative_prompt="blurry, distorted, low quality",
        )

        print("\n=== Starting Veo Generation with Base64 Image ===")
        print(f"Prompt: {input_data.prompt}")
        print(f"Image mime_type: {sample_image.mime_type}")
        print(f"Image base64 length: {len(sample_image.base64)} chars")

        result = await service.generate(input_data, config)

        print(f"Video ID: {result.id}")
        print(f"Status: {result.status}")

        save_result("veo_with_image", result, output_dir)

        assert result.id is not None
        assert result.status in ["queued", "in_progress"]


class TestBatchIntegration:
    """Integration tests for batch video generation."""

    @pytest.fixture(autouse=True)
    def skip_if_no_keys(self):
        """Skip tests if API keys are not set."""
        if not os.environ.get("OPENAI_API_KEY") or not os.environ.get("GOOGLE_API_KEY"):
            pytest.skip("Both OPENAI_API_KEY and GOOGLE_API_KEY required")

    @pytest.mark.asyncio
    async def test_batch_generation(self, service, output_dir):
        """Test generating videos from both providers in parallel."""
        config = GenerationConfig(duration=4, aspect_ratio="16:9")

        inputs = [
            (SoraInput(prompt="A cat sitting by a window watching rain"), 0),
            (VeoInput(prompt="A dog running through autumn leaves"), 1),
        ]

        print("\n=== Starting Batch Generation ===")
        results = await service.generate_batch(inputs, config)

        for result in results:
            print(f"\n[Input {result.input_index}] Provider: {result.provider}")
            print(f"  Video ID: {result.video.id}")
            print(f"  Status: {result.video.status}")
            save_result(f"batch_{result.provider}_{result.input_index}", result.video, output_dir)

        assert len(results) == 2
        assert all(r.video.id is not None for r in results)


if __name__ == "__main__":
    # Run a quick test
    async def main():
        output_dir = get_output_dir()
        service = VideoGenerationService()

        print("Testing video generation module...")
        print(f"Output directory: {output_dir}")

        # Check which API keys are available
        has_openai = bool(os.environ.get("OPENAI_API_KEY"))
        has_google = bool(os.environ.get("GOOGLE_API_KEY"))

        print(f"OpenAI API key: {'set' if has_openai else 'not set'}")
        print(f"Google API key: {'set' if has_google else 'not set'}")

        if has_openai:
            print("\n--- Testing Sora ---")
            result = await service.generate(
                SoraInput(prompt="A cat walking"),
                GenerationConfig(duration=4),
            )
            print(f"Sora result: {result.model_dump_json(indent=2)}")

        if has_google:
            print("\n--- Testing Veo ---")
            result = await service.generate(
                VeoInput(prompt="A dog running"),
                GenerationConfig(duration=4),
            )
            print(f"Veo result: {result.model_dump_json(indent=2)}")

    asyncio.run(main())
