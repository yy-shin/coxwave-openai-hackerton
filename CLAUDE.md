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

### ChatKit References
This project uses ChatKit Python SDK and ChatKit.js (specifically, @openai/chatkit-react) for chat interface between agents and user.
- ChatKit Python SDK: implements the ChatKit server, owns chat state, runs agents/tools, defines widget schemas and actions, and streams structured interaction events.
- ChatKit frontend (ChatKit.js / @openai/chatkit-react): client runtime that sends user input and widget actions, renders streamed events and widgets, and manages the chat UI.

**Frontend**: Use type definitions as primary reference.
- React bindings for ChatKit: `frontend/node_modules/.pnpm/@openai+chatkit-react@1.3.0_react-dom@19.2.1_react@19.2.1__react@19.2.1/node_modules/@openai/chatkit-react/dist/index.d.ts`
- Core ChatKit configuration types (Primary API reference): `frontend/node_modules/.pnpm/@openai+chatkit-react@1.3.0_react-dom@19.2.1_react@19.2.1__react@19.2.1/node_modules/@openai/chatkit/types/index.d.ts`
- Widget component types (JSON structure sent from backend): `frontend/node_modules/.pnpm/@openai+chatkit-react@1.3.0_react-dom@19.2.1_react@19.2.1__react@19.2.1/node_modules/@openai/chatkit/types/widgets.d.ts`

**Backend**: [Chatkit Python SDK documentation](https://github.com/openai/chatkit-python/blob/main/docs/index.md)
- Concepts: https://github.com/openai/chatkit-python/blob/main/docs/concepts
- Guides: https://github.com/openai/chatkit-python/tree/main/docs/guides

**External Resources (use WebFetch tool)**:
- [chatkit-python](https://github.com/openai/chatkit-python/)
- [chatkit-js](https://openai.github.io/chatkit-js/) 
- [openai-chatkit-starter-app](https://github.com/openai/openai-chatkit-starter-app)
- [openai-chatkit-advanced-samples](https://github.com/openai/openai-chatkit-advanced-samples)
- [ChatKit Guide](https://platform.openai.com/docs/guides/chatkit) — Official overview (requires OpenAI login)
