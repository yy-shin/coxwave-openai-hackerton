# Project Schema

> Schema for orchestrating multi-segment video generation for marketing ads.
> For the full video model specification with all parameters, see [video_model_spec.md](./video_model_spec.md).

## Overview

```
Project
├── title              (project name)
├── description        (vivid description including appeal type, considerations)
├── aspect_ratio       (16:9 or 9:16, default: 9:16)
├── total_duration     (total video length in seconds)
└── storyboard
    └── segments[]     (ordered list of video segments)
        ├── scene_description  (human-readable, not for AI)
        ├── duration           (segment duration in seconds)
        └── generation_inputs[1] (exactly 1 input: SoraInput | VeoInput)
            ├── SoraInput
            │   ├── provider: "sora"
            │   ├── model: sora-2 | sora-2-pro
            │   ├── prompt
            │   └── input_image
            │
            └── VeoInput
                ├── provider: "veo"
                ├── model: veo-3.1-*
                ├── prompt
                ├── input_image
                ├── negative_prompt
                ├── last_frame
                ├── reference_images
                └── num_outputs
```

## Hardcoded Defaults

| Parameter | Fixed Value | Notes |
|-----------|-------------|-------|
| `resolution` | 720p | Standard quality |
| `generate_audio` | true | Veo only, always enabled |
| `person_generation` | allow_all | Veo only, allow all people generation |

## Schema Definition

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Project",
  "description": "Top-level container for multi-segment video advertisement generation",
  "type": "object",
  "required": ["title", "description", "aspect_ratio", "total_duration", "storyboard"],
  "properties": {
    "title": {
      "type": "string",
      "description": "Project name/title"
    },
    "description": {
      "type": "string",
      "description": "Vivid description of the entire video (include appeal type, target audience, key considerations, visual style)"
    },
    "aspect_ratio": {
      "type": "string",
      "enum": ["16:9", "9:16"],
      "default": "9:16",
      "description": "Video aspect ratio for all segments (default: portrait)"
    },
    "total_duration": {
      "type": "integer",
      "minimum": 1,
      "maximum": 60,
      "description": "Total video length in seconds"
    },
    "storyboard": {
      "$ref": "#/$defs/Storyboard"
    }
  },
  "$defs": {
    "Storyboard": {
      "type": "object",
      "description": "Container for video segments",
      "required": ["segments"],
      "properties": {
        "segments": {
          "type": "array",
          "items": { "$ref": "#/$defs/VideoSegment" },
          "minItems": 1,
          "description": "Ordered list of video segments that compose the final video"
        }
      }
    },
    "VideoSegment": {
      "type": "object",
      "description": "A single segment of the video with multiple generation options",
      "required": ["scene_description", "duration", "generation_inputs"],
      "properties": {
        "scene_description": {
          "type": "string",
          "description": "Human-readable scene description for UI display (not sent to video AI models)"
        },
        "duration": {
          "type": "integer",
          "enum": [4, 6, 8, 12],
          "description": "Segment duration in seconds (6s: Veo only, 12s: Sora only)"
        },
        "generation_inputs": {
          "type": "array",
          "items": {
            "oneOf": [
              { "$ref": "#/$defs/SoraInput" },
              { "$ref": "#/$defs/VeoInput" }
            ]
          },
          "minItems": 1,
          "maxItems": 1,
          "description": "Single generation input for this segment"
        }
      }
    },
    "SoraInput": {
      "type": "object",
      "description": "Video generation input for Sora API",
      "required": ["provider", "prompt"],
      "properties": {
        "provider": {
          "const": "sora",
          "description": "Sora video generation API"
        },
        "model": {
          "type": "string",
          "enum": ["sora-2", "sora-2-pro"],
          "description": "Sora model identifier"
        },
        "prompt": {
          "type": "string",
          "maxLength": 4096,
          "description": "Text description of video content for AI model"
        },
        "input_image": {
          "$ref": "#/$defs/ImageInput",
          "description": "First frame / starting image"
        }
      }
    },
    "VeoInput": {
      "type": "object",
      "description": "Video generation input for Veo API",
      "required": ["provider", "prompt"],
      "properties": {
        "provider": {
          "const": "veo",
          "description": "Veo video generation API"
        },
        "model": {
          "type": "string",
          "enum": ["veo-3.1-generate-001", "veo-3.1-fast-generate-001", "veo-3.1-generate-preview", "veo-3.1-fast-generate-preview"],
          "description": "Veo model identifier"
        },
        "prompt": {
          "type": "string",
          "maxLength": 4096,
          "description": "Text description of video content for AI model"
        },
        "input_image": {
          "$ref": "#/$defs/ImageInput",
          "description": "First frame / starting image"
        },
        "negative_prompt": {
          "type": "string",
          "description": "What NOT to include"
        },
        "last_frame": {
          "$ref": "#/$defs/ImageInput",
          "description": "Last frame for interpolation"
        },
        "reference_images": {
          "type": "array",
          "items": { "$ref": "#/$defs/ImageInput" },
          "maxItems": 3,
          "description": "Subject/character reference images"
        },
        "num_outputs": {
          "type": "integer",
          "minimum": 1,
          "maximum": 4,
          "default": 1,
          "description": "Number of videos to generate per input"
        }
      }
    },
    "ImageInput": {
      "type": "object",
      "required": ["file_path"],
      "properties": {
        "file_path": {
          "type": "string",
          "description": "Local file path to the image"
        }
      }
    }
  }
}
```

## Example Project

### Cookie Run Marketing Video (24 seconds)

```json
{
  "title": "Cookie Run Transformation Ad",
  "description": "A high-energy game marketing video showcasing Cookie Run character transformation. Appeals to casual mobile gamers aged 18-35 through vibrant colors, dynamic action sequences, and character progression fantasy. Style: 2D animated with cel-shading effects.",
  "aspect_ratio": "9:16",
  "total_duration": 24,
  "storyboard": {
    "segments": [
      {
        "scene_description": "Opening shot: Cookie character appears in a magical forest",
        "duration": 8,
        "generation_inputs": [
          {
            "provider": "veo",
            "prompt": "A cute 2D animated cookie character with big eyes stands in a colorful magical forest, sunlight filtering through trees, whimsical atmosphere, smooth animation, vibrant colors",
            "negative_prompt": "blurry, low quality, distorted, realistic",
            "reference_images": [
              { "file_path": "/path/to/cookie_character.png" }
            ]
          }
        ]
      },
      {
        "scene_description": "Transformation: Cookie gains superpowers with glowing effects",
        "duration": 8,
        "generation_inputs": [
          {
            "provider": "veo",
            "prompt": "The cookie character begins glowing with golden energy, magical transformation sequence, swirling particles, dynamic camera movement, epic power-up moment, 2D animated style",
            "negative_prompt": "blurry, distorted",
            "input_image": {
              "file_path": "/path/to/transformation_start.png"
            }
          }
        ]
      },
      {
        "scene_description": "Finale: Superhero cookie in action pose with logo reveal",
        "duration": 8,
        "generation_inputs": [
          {
            "provider": "sora",
            "prompt": "Superhero cookie character in heroic pose, cape flowing, magical energy surrounding them, camera pulls back to reveal Cookie Run logo, celebratory particle effects, 2D animated style"
          }
        ]
      }
    ]
  }
}
```

## Parameter Summary

### Project (Top-Level)

| Parameter | Required | Description |
|-----------|----------|-------------|
| `title` | Yes | Project name |
| `description` | Yes | Vivid description of entire video concept |
| `aspect_ratio` | Yes | `16:9` or `9:16` for all segments |
| `total_duration` | Yes | Total length in seconds (1-60) |
| `storyboard` | Yes | Contains the segments array |

### VideoSegment

| Parameter | Required | Description |
|-----------|----------|-------------|
| `scene_description` | Yes | Human-readable scene description (UI only) |
| `duration` | Yes | 4, 6, 8, or 12 seconds |
| `generation_inputs` | Yes | Array of SoraInput or VeoInput objects |

### SoraInput

| Parameter | Required | Description |
|-----------|----------|-------------|
| `provider` | Yes | Must be `"sora"` |
| `prompt` | Yes | Text description for AI model |
| `model` | No | `sora-2` or `sora-2-pro` |
| `input_image` | No | First frame image |

### VeoInput

| Parameter | Required | Description |
|-----------|----------|-------------|
| `provider` | Yes | Must be `"veo"` |
| `prompt` | Yes | Text description for AI model |
| `model` | No | `veo-3.1-generate-001`, `veo-3.1-fast-generate-001`, etc. |
| `input_image` | No | First frame image |
| `negative_prompt` | No | What NOT to include |
| `last_frame` | No | Last frame for interpolation |
| `reference_images` | No | Up to 3 subject reference images |
| `num_outputs` | No | 1-4 videos (default: 1) |
