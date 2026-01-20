# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Adding Dependencies

When adding new libraries, always search for the latest version on PyPI first.

## Project Overview

Video generation AI agent system for creating marketing/advertising videos. The system uses multi-agent workflows to orchestrate multiple video generation models (Sora, Veo, Kling) and produces high-quality videos up to 1 minute in length.

**Target Use Case:** Game marketing video ads (e.g., Cookie Run character transformation ads, viral marketing videos)

## Technology Stack

- **Backend/Agents:** Python 3.11+, OpenAI Agents SDK, uv (package manager)
- **Frontend:** Next.js, React, Tailwind CSS, shadcn/ui
- **Video Generation APIs:** Sora, Veo, Kling 2.5 Turbo
- **Image Generation/LLM:** GPT (OpenAI)

## Architecture

### Agent Workflow

```
User Request → Clarifying Questions → Plan/Storyboard → Prompt Generation →
Keyframe Image Generation → Video Model Selection → Video Generation →
User Selection → Final Video Assembly
```

### Components

1. **Frontend (Web UI)** - Multi-page interface:
   - Page 1: Request input and clarifying Q&A
   - Page 2: Storyboard display and review
   - Page 3: Per-segment video selection (3 clips per segment)
   - Page 4: Final assembled video playback

2. **Backend API** - Handles:
   - Web → Agent communication
   - Local directory as database storage
   - Unified interface for video generation APIs

3. **Agents** (OpenAI Agents SDK):
   - Storyboard generation tool
   - Video prompt writing tool
   - Video input analysis tool
   - Image generation tool
   - Handoff agents for storyboard writing and clarifying questions

### Video Generation Model Selection

- Different models have different strengths (e.g., Veo struggles with 2D animation)
- Agent should select appropriate model per video segment
- Use Gemini for seamless cuts between segments

## Input/Output Spec

**Inputs:**
- Reference video
- Reference images (e.g., character art)
- Text description
- Video aspect ratio (default: Portrait)
- Video length (default: 30 seconds, max: 60 seconds)

**Outputs:**
- Generated video
- Thumbnail
- Banner
- Marketing copy/scripts

## API References

- Sora: https://platform.openai.com/docs/guides/video-generation
- Sora API: https://platform.openai.com/docs/api-reference/videos
