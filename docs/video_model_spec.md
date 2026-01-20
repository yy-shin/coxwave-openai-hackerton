# Video Generation API Specifications

## Parameter Comparison: Sora vs Veo 3.1

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              SHARED PARAMETERS                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│  prompt          │ Text description of video content                           │
│  aspect_ratio    │ 16:9 (landscape) or 9:16 (portrait)                         │
│  duration        │ Video length in seconds                                     │
│  input_image     │ Reference image for first frame (image-to-video)            │
└─────────────────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────┐     ┌───────────────────────────────────────┐
│         SORA ONLY                 │     │           VEO 3.1 ONLY                │
├───────────────────────────────────┤     ├───────────────────────────────────────┤
│ • remix_video_id                  │     │ • negativePrompt                      │
│ • size (WxH format)               │     │ • resolution (720p/1080p/4k)          │
│                                   │     │ • lastFrame                           │
│                                   │     │ • referenceImages (up to 3)           │
│                                   │     │ • video (for extension)               │
│                                   │     │ • seed                                │
│                                   │     │ • sampleCount (1-4)                   │
│                                   │     │ • generateAudio                       │
│                                   │     │ • personGeneration                    │
│                                   │     │ • resizeMode                          │
│                                   │     │ • compressionQuality                  │
└───────────────────────────────────┘     └───────────────────────────────────────┘

### Input Reference Comparison

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           INPUT REFERENCES                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                           │    SORA         │       VEO 3.1                     │
├───────────────────────────┼─────────────────┼───────────────────────────────────┤
│ First Frame Image         │    1 ✅         │       1 ✅                        │
│ Last Frame Image          │    ❌           │       1 ✅                        │
│ Reference Images (subject)│    ❌           │       up to 3 ✅                  │
│ Video (for extension)     │    ❌           │       1 ✅                        │
├───────────────────────────┼─────────────────┼───────────────────────────────────┤
│ MAX TOTAL INPUTS          │    1            │       5 (1+1+3) + 1 video         │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Sora API (OpenAI)

> Source: https://platform.openai.com/docs/api-reference/videos

### Models

| Model | Description |
|-------|-------------|
| `sora-2` | Default. Powerful media generation with synced audio |
| `sora-2-pro` | Most advanced model with richer details and synced audio |

### Create Video

**Endpoint:** `POST https://api.openai.com/v1/videos`

| Parameter | Type | Required | Default | Valid Values | Description |
|-----------|------|----------|---------|--------------|-------------|
| `model` | string | No | `sora-2` | `sora-2`, `sora-2-pro` | Model to use |
| `prompt` | string | **Yes** | - | Natural language | Description of scene, subject, action |
| `seconds` | integer | No | `4` | `4`, `8`, `12` | Video duration |
| `size` | string | No | `720x1280` | See below | Output resolution (WxH) |
| `input_reference` | file | No | - | jpeg, png, webp | Reference image for first frame |

#### Size Options

| Aspect Ratio | Resolutions |
|--------------|-------------|
| 9:16 (Portrait) | `720x1280`, `1024x1792` |
| 16:9 (Landscape) | `1280x720`, `1792x1024` |

### Remix Video

**Endpoint:** `POST https://api.openai.com/v1/videos/{video_id}/remix`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `video_id` | string | **Yes** | ID of completed video to remix |
| `prompt` | string | **Yes** | Updated prompt describing the change |

> Remix reuses original structure, continuity, and composition while applying modifications.
> Best results with single, well-defined changes.

### API Endpoints Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/videos` | POST | Create new video |
| `/v1/videos/{video_id}` | GET | Get video status |
| `/v1/videos/{video_id}/content/video.mp4` | GET | Download finished video |
| `/v1/videos` | GET | List videos with pagination |
| `/v1/videos/{video_id}/remix` | POST | Remix existing video |

### Job Status

| Status | Description |
|--------|-------------|
| `queued` | Waiting to start |
| `in_progress` | Currently processing |
| `completed` | Ready for download |
| `failed` | Generation failed |

---

## Veo 3.1 API (Google)

> Source: https://ai.google.dev/gemini-api/docs/video

### Models

| Model | Description |
|-------|-------------|
| `veo-3.1-generate-001` | Standard production model |
| `veo-3.1-fast-generate-001` | Faster variant |
| `veo-3.1-generate-preview` | Preview with 4K support |
| `veo-3.1-fast-generate-preview` | Preview faster variant |

### Create Video

| Parameter | Type | Required | Default | Valid Values | Description |
|-----------|------|----------|---------|--------------|-------------|
| `prompt` | string | **Yes** | - | Max 1,024 tokens | Text description (supports audio cues) |
| `negativePrompt` | string | No | - | Any text | What NOT to include |
| `durationSeconds` | integer | No | `8` | `4`, `6`, `8` | Video duration |
| `resolution` | string | No | `720p` | `720p`, `1080p`, `4k` | Output resolution |
| `aspectRatio` | string | No | `16:9` | `16:9`, `9:16` | Aspect ratio |
| `sampleCount` | integer | No | `1` | `1-4` | Number of videos to generate |
| `seed` | uint32 | No | - | 0-4,294,967,295 | For deterministic generation |
| `generateAudio` | boolean | No | - | true/false | Enable audio generation |
| `personGeneration` | string | No | `allow_adult` | `allow_adult`, `dont_allow`, `allow_all` | People generation control |
| `resizeMode` | string | No | `pad` | `pad`, `crop` | Image resize method |
| `compressionQuality` | string | No | `optimized` | `optimized`, `lossless` | Output compression |

### Input Options

| Input Type | Parameter | Max Count | Description |
|------------|-----------|-----------|-------------|
| First Frame | `image` | 1 | Image to animate (720p+, 16:9 or 9:16) |
| Last Frame | `lastFrame` | 1 | Final frame for interpolation |
| Reference Images | `referenceImages` | 3 | Subject/character reference |
| Video Extension | `video` | 1 | Extend existing video (MP4, 1-30s, 24fps) |

### Special Features

- **First/Last Frame**: Interpolate between specified start and end frames
- **Video Extension**: Extend up to 148 seconds total
- **Reference Images**: Preserve subject appearance across video

---

## Unified Parameter Mapping

For building a unified interface, map parameters as follows:

```
┌──────────────────┬─────────────────────┬─────────────────────────┐
│ Unified Param    │ Sora                │ Veo 3.1                 │
├──────────────────┼─────────────────────┼─────────────────────────┤
│ prompt           │ prompt              │ prompt                  │
│ duration         │ seconds (4,8,12)    │ durationSeconds (4,6,8) │
│ aspect_ratio     │ (derived from size) │ aspectRatio             │
│ resolution       │ size                │ resolution              │
│ input_image      │ input_reference     │ image                   │
│ model            │ model               │ model                   │
│ negative_prompt  │ N/A                 │ negativePrompt          │
│ last_frame       │ N/A                 │ lastFrame               │
│ reference_images │ N/A                 │ referenceImages         │
│ remix_source     │ remix_video_id      │ video (extension)       │
│ num_outputs      │ N/A                 │ sampleCount             │
│ seed             │ N/A                 │ seed                    │
└──────────────────┴─────────────────────┴─────────────────────────┘
```

### Duration Compatibility

| Seconds | Sora | Veo 3.1 |
|---------|------|---------|
| 4       | ✅   | ✅      |
| 6       | ❌   | ✅      |
| 8       | ✅   | ✅      |
| 12      | ✅   | ❌      |

### Resolution Compatibility

| Resolution | Sora | Veo 3.1 |
|------------|------|---------|
| 720p       | ✅   | ✅      |
| 1080p      | ✅ (1792x1024) | ✅ |
| 4K         | ❌   | ✅ (preview only) |

---

## Unified JSON Schema (Full Spec)

> **Note:** This is the **full specification** covering all possible parameters for both APIs.
> A simplified version for common use cases will be added later.

### Schema Definition

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "VideoGenerationRequest",
  "description": "Unified schema for Sora and Veo 3.1 video generation APIs (Full Spec)",
  "type": "object",
  "required": ["provider", "prompt"],
  "properties": {
    "provider": {
      "type": "string",
      "enum": ["sora", "veo"],
      "description": "Target video generation API"
    },
    "model": {
      "type": "string",
      "description": "Model identifier (provider-specific)",
      "oneOf": [
        { "enum": ["sora-2", "sora-2-pro"] },
        { "enum": ["veo-3.1-generate-001", "veo-3.1-fast-generate-001", "veo-3.1-generate-preview", "veo-3.1-fast-generate-preview"] }
      ]
    },
    "prompt": {
      "type": "string",
      "maxLength": 4096,
      "description": "Text description of video content"
    },
    "aspect_ratio": {
      "type": "string",
      "enum": ["16:9", "9:16"],
      "default": "16:9",
      "description": "Video aspect ratio"
    },
    "duration": {
      "type": "integer",
      "enum": [4, 6, 8, 12],
      "default": 4,
      "description": "Video duration in seconds (6s: Veo only, 12s: Sora only)"
    },
    "resolution": {
      "type": "string",
      "enum": ["720p", "1080p", "4k"],
      "default": "720p",
      "description": "Output resolution (4k: Veo preview only)"
    },
    "input_image": {
      "$ref": "#/$defs/ImageInput",
      "description": "First frame reference image"
    },
    "negative_prompt": {
      "type": "string",
      "description": "What NOT to include (Veo only)"
    },
    "last_frame": {
      "$ref": "#/$defs/ImageInput",
      "description": "Last frame for interpolation (Veo only)"
    },
    "reference_images": {
      "type": "array",
      "items": { "$ref": "#/$defs/ImageInput" },
      "maxItems": 3,
      "description": "Subject/character reference images (Veo only)"
    },
    "remix_video_id": {
      "type": "string",
      "description": "Previously generated video ID for remix (Sora only)"
    },
    "extension_video": {
      "$ref": "#/$defs/VeoExtensionInput",
      "description": "Source video for extension (Veo only)"
    },
    "seed": {
      "type": "integer",
      "minimum": 0,
      "maximum": 4294967295,
      "description": "Seed for deterministic generation (Veo only)"
    },
    "num_outputs": {
      "type": "integer",
      "minimum": 1,
      "maximum": 4,
      "default": 1,
      "description": "Number of videos to generate (Veo only)"
    },
    "generate_audio": {
      "type": "boolean",
      "description": "Enable audio generation (Veo only)"
    },
    "person_generation": {
      "type": "string",
      "enum": ["allow_adult", "dont_allow", "allow_all"],
      "default": "allow_adult",
      "description": "People/face generation control (Veo only)"
    }
  },
  "$defs": {
    "ImageInput": {
      "type": "object",
      "properties": {
        "url": {
          "type": "string",
          "format": "uri",
          "description": "URL to image file"
        },
        "base64": {
          "type": "string",
          "description": "Base64-encoded image data"
        },
        "mime_type": {
          "type": "string",
          "enum": ["image/jpeg", "image/png", "image/webp"],
          "description": "Image MIME type"
        }
      },
      "oneOf": [
        { "required": ["url"] },
        { "required": ["base64", "mime_type"] }
      ]
    },
    "VeoExtensionInput": {
      "type": "object",
      "description": "Source video for Veo extension (MP4, 1-30s, 24fps, 720p/1080p)",
      "properties": {
        "url": {
          "type": "string",
          "format": "uri",
          "description": "URL to video file"
        },
        "base64": {
          "type": "string",
          "description": "Base64-encoded video data"
        }
      },
      "oneOf": [
        { "required": ["url"] },
        { "required": ["base64"] }
      ]
    }
  }
}
```

### Example Requests

#### Sora Text-to-Video

```json
{
  "provider": "sora",
  "model": "sora-2",
  "prompt": "A golden retriever running on a beach at sunset, cinematic lighting",
  "aspect_ratio": "16:9",
  "duration": 8,
  "resolution": "720p"
}
```

#### Sora Image-to-Video

```json
{
  "provider": "sora",
  "model": "sora-2-pro",
  "prompt": "The character starts dancing with smooth movements",
  "aspect_ratio": "9:16",
  "duration": 4,
  "resolution": "1080p",
  "input_image": {
    "url": "https://example.com/character.png"
  }
}
```

#### Sora Remix

```json
{
  "provider": "sora",
  "model": "sora-2",
  "prompt": "Change the background to a futuristic cityscape",
  "remix_video_id": "video_abc123"
}
```

#### Veo Text-to-Video

```json
{
  "provider": "veo",
  "model": "veo-3.1-generate-001",
  "prompt": "A 2D animated cookie character transforming into a superhero",
  "negative_prompt": "blurry, low quality, distorted",
  "aspect_ratio": "9:16",
  "duration": 8,
  "resolution": "1080p",
  "num_outputs": 2,
  "generate_audio": true
}
```

#### Veo with Reference Images

```json
{
  "provider": "veo",
  "model": "veo-3.1-generate-preview",
  "prompt": "The character walks through a magical forest",
  "aspect_ratio": "16:9",
  "duration": 6,
  "resolution": "720p",
  "input_image": {
    "base64": "<base64_data>",
    "mime_type": "image/png"
  },
  "reference_images": [
    { "url": "https://example.com/character_front.png" },
    { "url": "https://example.com/character_side.png" },
    { "url": "https://example.com/character_back.png" }
  ],
  "seed": 12345
}
```

#### Veo First/Last Frame Interpolation

```json
{
  "provider": "veo",
  "model": "veo-3.1-generate-001",
  "prompt": "Smooth transition from day to night in a city skyline",
  "aspect_ratio": "16:9",
  "duration": 8,
  "resolution": "720p",
  "input_image": {
    "url": "https://example.com/city_day.png"
  },
  "last_frame": {
    "url": "https://example.com/city_night.png"
  }
}
```

### Parameter Availability by Provider

```
┌─────────────────────┬─────────┬─────────┐
│ Parameter           │  Sora   │  Veo    │
├─────────────────────┼─────────┼─────────┤
│ provider            │   ✅    │   ✅    │
│ model               │   ✅    │   ✅    │
│ prompt              │   ✅    │   ✅    │
│ aspect_ratio        │   ✅    │   ✅    │
│ duration            │   ✅    │   ✅    │
│ resolution          │   ✅    │   ✅    │
│ input_image         │   ✅    │   ✅    │
├─────────────────────┼─────────┼─────────┤
│ negative_prompt     │   ❌    │   ✅    │
│ last_frame          │   ❌    │   ✅    │
│ reference_images    │   ❌    │   ✅    │
│ seed                │   ❌    │   ✅    │
│ num_outputs         │   ❌    │   ✅    │
│ generate_audio      │   ❌    │   ✅    │
│ person_generation   │   ❌    │   ✅    │
├─────────────────────┼─────────┼─────────┤
│ remix_video_id      │   ✅    │   ❌    │
│ extension_video     │   ❌    │   ✅    │
└─────────────────────┴─────────┴─────────┘
```

---

## Project Schema

For the project schema optimized for multi-segment video generation, see [project_schema.md](./project_schema.md).
