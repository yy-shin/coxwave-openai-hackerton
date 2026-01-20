# Video Generations Schema

> Schema for storing video generation results from multiple providers (Sora, Veo).
> For the project input schema, see [project_schema.md](./project_schema.md).

## Overview

```
VideoGenerations
├── project_id          (reference to source project)
├── created_at          (timestamp)
├── status              (overall status)
└── segments[]          (array of SegmentGeneration)
    └── SegmentGeneration
        ├── segment_index       (position in storyboard)
        ├── scene_description   (copied from project)
        ├── status              (segment-level status)
        └── generation_results[] (multiple results can share same input_index)
            └── GenerationResult
                ├── input_index         (which generation_input this maps to)
                ├── provider            ("sora" | "veo")
                └── video               (single GeneratedVideo)
                    └── GeneratedVideo
                        ├── id                  (provider's video ID)
                        ├── status              (queued|in_progress|completed|failed)
                        ├── progress            (0-100, optional)
                        ├── created_at          (timestamp)
                        ├── video_url           (download URL)
                        ├── thumbnail_url       (optional)
                        ├── duration            (seconds)
                        ├── resolution          (e.g., "720p", "1280x720")
                        ├── has_audio           (boolean)
                        ├── selected            (boolean, user selection)
                        └── error               (optional, failure reason)
```

## Provider-Specific Behavior

### Sora Response Mapping

| Sora Field | GeneratedVideo Field |
|------------|---------------------|
| `id` | `id` |
| `status` | `status` (direct mapping) |
| `progress` | `progress` |
| `created_at` | `created_at` (convert from Unix timestamp) |
| `size` | `resolution` (e.g., "1024x1792") |
| `seconds` | `duration` |
| Video download endpoint | `video_url` |

### Veo Response Mapping

| Veo Field | GeneratedVideo Field |
|-----------|---------------------|
| Operation name | `id` |
| `generated_videos[].video.uri` | `video_url` |
| Operation status | `status` (map to enum) |
| `generated_videos[].video.mimeType` | (not stored, always mp4) |

## Schema Definition

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "VideoGenerations",
  "description": "Container for video generation results linked to a project",
  "type": "object",
  "required": ["project_id", "created_at", "segments"],
  "properties": {
    "project_id": {
      "type": "string",
      "description": "Reference to the source project"
    },
    "created_at": {
      "type": "string",
      "format": "date-time",
      "description": "Timestamp when generation was initiated"
    },
    "status": {
      "type": "string",
      "enum": ["pending", "in_progress", "completed", "failed"],
      "description": "Overall status of all video generations"
    },
    "segments": {
      "type": "array",
      "items": { "$ref": "#/$defs/SegmentGeneration" },
      "minItems": 1,
      "description": "Generation results for each segment in the storyboard"
    }
  },
  "$defs": {
    "SegmentGeneration": {
      "type": "object",
      "description": "Video generation results for a single storyboard segment",
      "required": ["segment_index", "generation_results"],
      "properties": {
        "segment_index": {
          "type": "integer",
          "minimum": 0,
          "description": "Position of this segment in the storyboard (0-indexed)"
        },
        "scene_description": {
          "type": "string",
          "description": "Human-readable scene description (copied from project)"
        },
        "status": {
          "type": "string",
          "enum": ["pending", "in_progress", "completed", "failed"],
          "description": "Status of generation for this segment"
        },
        "generation_results": {
          "type": "array",
          "items": { "$ref": "#/$defs/GenerationResult" },
          "minItems": 1,
          "description": "Results for each generation output (multiple results can share the same input_index)"
        }
      }
    },
    "GenerationResult": {
      "type": "object",
      "description": "Single video output from a generation_input",
      "required": ["input_index", "provider", "video"],
      "properties": {
        "input_index": {
          "type": "integer",
          "minimum": 0,
          "description": "Index of the generation_input this result corresponds to"
        },
        "provider": {
          "type": "string",
          "enum": ["sora", "veo"],
          "description": "Video generation provider used"
        },
        "video": {
          "$ref": "#/$defs/GeneratedVideo",
          "description": "The generated video output"
        }
      }
    },
    "GeneratedVideo": {
      "type": "object",
      "description": "Individual generated video result",
      "required": ["id", "status", "created_at"],
      "properties": {
        "id": {
          "type": "string",
          "description": "Provider's unique video identifier"
        },
        "status": {
          "type": "string",
          "enum": ["queued", "in_progress", "completed", "failed"],
          "description": "Generation status for this video"
        },
        "progress": {
          "type": "integer",
          "minimum": 0,
          "maximum": 100,
          "description": "Generation progress percentage (optional)"
        },
        "created_at": {
          "type": "string",
          "format": "date-time",
          "description": "Timestamp when generation started"
        },
        "video_url": {
          "type": "string",
          "format": "uri",
          "description": "Download URL for the generated video"
        },
        "thumbnail_url": {
          "type": "string",
          "format": "uri",
          "description": "URL for video thumbnail (optional)"
        },
        "duration": {
          "type": "integer",
          "description": "Video duration in seconds"
        },
        "resolution": {
          "type": "string",
          "description": "Video resolution (e.g., '720p', '1280x720')"
        },
        "has_audio": {
          "type": "boolean",
          "description": "Whether the video contains audio"
        },
        "selected": {
          "type": "boolean",
          "default": false,
          "description": "Whether user has selected this video for final assembly"
        },
        "error": {
          "type": "string",
          "description": "Error message if generation failed"
        }
      }
    }
  }
}
```

## Example Video Generations

### Cookie Run Marketing Video (3 segments, multiple outputs per input)

```json
{
  "project_id": "project_abc123",
  "created_at": "2025-01-20T10:30:00Z",
  "status": "completed",
  "segments": [
    {
      "segment_index": 0,
      "scene_description": "Opening shot: Cookie character appears in a magical forest",
      "status": "completed",
      "generation_results": [
        {
          "input_index": 0,
          "provider": "veo",
          "video": {
            "id": "veo_gen_001",
            "status": "completed",
            "created_at": "2025-01-20T10:30:05Z",
            "video_url": "https://storage.googleapis.com/veo-outputs/video_001.mp4",
            "thumbnail_url": "https://storage.googleapis.com/veo-outputs/thumb_001.jpg",
            "duration": 8,
            "resolution": "720p",
            "has_audio": true,
            "selected": true
          }
        },
        {
          "input_index": 0,
          "provider": "veo",
          "video": {
            "id": "veo_gen_002",
            "status": "completed",
            "created_at": "2025-01-20T10:30:05Z",
            "video_url": "https://storage.googleapis.com/veo-outputs/video_002.mp4",
            "thumbnail_url": "https://storage.googleapis.com/veo-outputs/thumb_002.jpg",
            "duration": 8,
            "resolution": "720p",
            "has_audio": true,
            "selected": false
          }
        },
        {
          "input_index": 1,
          "provider": "sora",
          "video": {
            "id": "video_sora_101",
            "status": "completed",
            "progress": 100,
            "created_at": "2025-01-20T10:30:10Z",
            "video_url": "https://api.openai.com/v1/videos/video_sora_101/content/video.mp4",
            "duration": 8,
            "resolution": "1280x720",
            "has_audio": false,
            "selected": false
          }
        }
      ]
    },
    {
      "segment_index": 1,
      "scene_description": "Transformation: Cookie gains superpowers with glowing effects",
      "status": "completed",
      "generation_results": [
        {
          "input_index": 0,
          "provider": "veo",
          "video": {
            "id": "veo_gen_004",
            "status": "completed",
            "created_at": "2025-01-20T10:32:00Z",
            "video_url": "https://storage.googleapis.com/veo-outputs/video_004.mp4",
            "thumbnail_url": "https://storage.googleapis.com/veo-outputs/thumb_004.jpg",
            "duration": 8,
            "resolution": "720p",
            "has_audio": true,
            "selected": true
          }
        }
      ]
    },
    {
      "segment_index": 2,
      "scene_description": "Finale: Superhero cookie in action pose with logo reveal",
      "status": "completed",
      "generation_results": [
        {
          "input_index": 0,
          "provider": "sora",
          "video": {
            "id": "video_sora_789",
            "status": "completed",
            "progress": 100,
            "created_at": "2025-01-20T10:34:00Z",
            "video_url": "https://api.openai.com/v1/videos/video_sora_789/content/video.mp4",
            "duration": 8,
            "resolution": "1280x720",
            "has_audio": false,
            "selected": true
          }
        },
        {
          "input_index": 0,
          "provider": "sora",
          "video": {
            "id": "video_sora_790",
            "status": "completed",
            "progress": 100,
            "created_at": "2025-01-20T10:34:00Z",
            "video_url": "https://api.openai.com/v1/videos/video_sora_790/content/video.mp4",
            "duration": 8,
            "resolution": "1280x720",
            "has_audio": false,
            "selected": false
          }
        }
      ]
    }
  ]
}
```

## Parameter Summary

### VideoGenerations (Top-Level)

| Parameter | Required | Description |
|-----------|----------|-------------|
| `project_id` | Yes | Reference to source project |
| `created_at` | Yes | ISO 8601 timestamp |
| `status` | No | Overall status: `pending`, `in_progress`, `completed`, `failed` |
| `segments` | Yes | Array of SegmentGeneration objects |

### SegmentGeneration

| Parameter | Required | Description |
|-----------|----------|-------------|
| `segment_index` | Yes | Position in storyboard (0-indexed) |
| `scene_description` | No | Human-readable scene description |
| `status` | No | Segment-level status |
| `generation_results` | Yes | Array of GenerationResult objects |

### GenerationResult

| Parameter | Required | Description |
|-----------|----------|-------------|
| `input_index` | Yes | Index of corresponding generation_input (0-indexed) |
| `provider` | Yes | `sora` or `veo` |
| `video` | Yes | Single GeneratedVideo object |

### GeneratedVideo

| Parameter | Required | Description |
|-----------|----------|-------------|
| `id` | Yes | Provider's video identifier |
| `status` | Yes | `queued`, `in_progress`, `completed`, `failed` |
| `progress` | No | Generation progress (0-100) |
| `created_at` | Yes | ISO 8601 timestamp |
| `video_url` | No | Download URL (available when completed) |
| `thumbnail_url` | No | Thumbnail image URL |
| `duration` | No | Video length in seconds |
| `resolution` | No | Video resolution string |
| `has_audio` | No | Whether video contains audio |
| `selected` | No | User selection for final assembly (default: false) |
| `error` | No | Error message if failed |

## Status Transitions

```
GeneratedVideo: queued → in_progress → completed
                              ↓
                           failed

SegmentGeneration: pending → in_progress → completed
                                  ↓
                               failed

VideoGenerations: pending → in_progress → completed
                                ↓
                             failed
```

## Relationship to Project Schema

```
Project                              VideoGenerations
├── storyboard                       ├── project_id ─────────────────┐
│   └── segments[i]          ───────►│   └── segments[i]             │
│       ├── scene_description        │       ├── segment_index: i    │
│       ├── duration                 │       ├── scene_description   │
│       └── generation_inputs[j] ───►│       └── generation_results[]
│           ├── provider             │           ├── input_index: j  (multiple can share same j)
│           └── prompt               │           ├── provider
│                                    │           └── video
└── title ◄──────────────────────────┘
```

## Usage in Page 3 UI

The `generation_results` array with `video.selected` field supports the Page 3 video selection interface:

1. Display all `generation_results` for each segment (grouped by `input_index` if desired)
2. User selects one video per segment (`video.selected: true`)
3. Selected videos are used for final video assembly
