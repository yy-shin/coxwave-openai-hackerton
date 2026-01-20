"""Video generation agent with ChatKit integration."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated, Any, Callable, List

from agents import Agent, ModelSettings, RunContextWrapper, StopAtTools, function_tool
from chatkit.agents import AgentContext
from chatkit.types import (
    AssistantMessageContent,
    AssistantMessageItem,
    ClientEffectEvent,
    HiddenContextItem,
    ThreadItemDoneEvent,
)
from openai.types import Reasoning
from pydantic import BaseModel, ConfigDict, Field

from .video_project_state import ProjectPhase, VideoProjectState, VideoSegment


class SegmentInput(BaseModel):
    """Input model for a storyboard segment."""

    id: str = Field(description="Unique segment ID (e.g., 'seg_1')")
    description: str = Field(description="What happens in this segment")
    duration_sec: float = Field(default=5.0, description="Duration in seconds (3-8 recommended)")
    transition: str = Field(default="cut", description="Transition type ('cut', 'fade', 'dissolve')")
    key_elements: List[str] = Field(default_factory=list, description="List of key visual elements")
    video_model: str = Field(default="sora", description="Preferred model ('sora', 'veo', 'kling')")
from .video_project_store import VideoProjectStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

INSTRUCTIONS: str = """
You are OvenAI, an expert video advertisement creation assistant helping users create
high-quality marketing videos for games and products.

## Workflow
1. **Clarifying Phase**: Ask clarifying questions to understand:
   - What product/game is being advertised
   - Target audience and platform
   - Desired tone and style
   - Key selling points to highlight
   - Reference materials (videos, images)
   - Aspect ratio (default: 9:16 portrait)
   - Target duration (default: 30 seconds, max: 60 seconds)

2. **Storyboard Phase**: Once you have enough information:
   - Create a detailed storyboard with 4-8 segments
   - Each segment should be 3-8 seconds
   - Call `create_storyboard` to display the visual storyboard
   - Wait for user approval before proceeding

3. **Generation Phase**: After approval:
   - Generate keyframe images for each segment
   - Select appropriate video model for each segment:
     - Sora: realistic/cinematic footage
     - Veo: stylized/artistic content
     - Kling: 2D animation/game footage
   - Call `start_video_generation` to begin the process

4. **Selection Phase**: Present video variants to user:
   - Show 3 variants per segment
   - Use `show_video_selection` widget
   - Let user choose their preferred version

5. **Assembly Phase**: After all selections:
   - Assemble final video
   - Generate thumbnail and banner
   - Create marketing copy
   - Show final result with `show_final_output`

## Tools
- `get_project_status`: Check current project state before deciding what to do
- `set_project_details`: Set project title, aspect ratio, duration, and description
- `create_storyboard`: Create and display storyboard with segments
- `start_video_generation`: Start video generation after storyboard approval
- `show_video_selection`: Show video selection options for a segment
- `show_final_output`: Display final assembled video and outputs

## Important Notes
- Keep responses concise and professional
- Always confirm understanding before proceeding to next phase
- Video models: Sora (realistic/cinematic), Veo (stylized/artistic), Kling (2D animation/game footage)
- Once an action has been performed, it will be reflected as a tag in the thread content:
  - <STORYBOARD_CREATED>: Storyboard was created
  - <STORYBOARD_APPROVED>: User approved storyboard
  - <VIDEO_GENERATION_STARTED>: Video generation began
  - <SEGMENT_SELECTED>: User selected a video variant
  - <PROJECT_COMPLETE>: Final output delivered
"""

MODEL = "gpt-5.2"


class VideoAgentContext(AgentContext):
    """Agent context with access to video project store."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    projects: Annotated[VideoProjectStore, Field(exclude=True)]


async def _get_state(ctx: RunContextWrapper[VideoAgentContext]) -> VideoProjectState:
    """Get the current project state for this thread."""
    thread_id = ctx.context.thread.id
    return await ctx.context.projects.load(thread_id)


async def _update_state(
    ctx: RunContextWrapper[VideoAgentContext],
    mutator: Callable[[VideoProjectState], None],
) -> VideoProjectState:
    """Update the project state and return the new state."""
    thread_id = ctx.context.thread.id
    return await ctx.context.projects.mutate(thread_id, mutator)


async def _sync_status(
    ctx: RunContextWrapper[VideoAgentContext],
    state: VideoProjectState,
    flash: str | None = None,
) -> None:
    """Stream a client effect to sync the project status."""
    await ctx.context.stream(
        ClientEffectEvent(
            name="update_project_status",
            data={
                "state": state.to_payload(ctx.context.thread.id),
                "flash": flash,
            },
        )
    )


async def _add_hidden_context(ctx: RunContextWrapper[VideoAgentContext], content: str) -> None:
    """Add a hidden context item for preserving action history."""
    thread = ctx.context.thread
    request_context = ctx.context.request_context
    await ctx.context.store.add_thread_item(
        thread.id,
        HiddenContextItem(
            id=ctx.context.store.generate_item_id("message", thread, request_context),
            thread_id=thread.id,
            created_at=datetime.now(),
            content=content,
        ),
        context=request_context,
    )


@function_tool(
    description_override="Get the current project status and phase. No parameters."
)
async def get_project_status(
    ctx: RunContextWrapper[VideoAgentContext],
) -> dict[str, Any]:
    """Return the current project state as a payload."""
    logger.info("[TOOL CALL] get_project_status")
    state = await _get_state(ctx)
    return state.to_payload(ctx.context.thread.id)


@function_tool(
    description_override=(
        "Set project details like title, aspect ratio, duration, and description.\n"
        "- `title`: Project title\n"
        "- `aspect_ratio`: Video aspect ratio (e.g., '9:16', '16:9', '1:1')\n"
        "- `target_duration_sec`: Target video duration in seconds (max 60)\n"
        "- `description`: Brief description of the video concept"
    )
)
async def set_project_details(
    ctx: RunContextWrapper[VideoAgentContext],
    title: str | None = None,
    aspect_ratio: str | None = None,
    target_duration_sec: int | None = None,
    description: str | None = None,
):
    """Set project configuration details."""
    logger.info("[TOOL CALL] set_project_details")

    def mutate(state: VideoProjectState) -> None:
        if title:
            state.title = title
        if aspect_ratio:
            state.aspect_ratio = aspect_ratio
        if target_duration_sec:
            state.target_duration_sec = min(target_duration_sec, 60)
        if description:
            state.description = description
        state.touch()

    state = await _update_state(ctx, mutate)

    # Update thread title
    if title:
        ctx.context.thread.title = title
        await ctx.context.store.save_thread(ctx.context.thread, ctx.context.request_context)

    await _sync_status(ctx, state, f"Project updated: {state.title}")
    return state.to_payload(ctx.context.thread.id)


@function_tool(
    description_override=(
        "Create and display a storyboard for the video.\n"
        "- `segments`: List of segment objects with id, description, duration_sec, transition, key_elements, video_model"
    )
)
async def create_storyboard(
    ctx: RunContextWrapper[VideoAgentContext],
    segments: List[SegmentInput],
):
    """Create a storyboard and display it to the user."""
    logger.info("[TOOL CALL] create_storyboard with %d segments", len(segments))

    video_segments = [
        VideoSegment(
            segment_id=seg.id,
            description=seg.description,
            duration_sec=seg.duration_sec,
            transition=seg.transition,
            key_elements=seg.key_elements,
            video_model=seg.video_model,
        )
        for seg in segments
    ]

    def mutate(state: VideoProjectState) -> None:
        state.segments = video_segments
        state.phase = ProjectPhase.STORYBOARD
        state.touch()

    state = await _update_state(ctx, mutate)
    await _add_hidden_context(ctx, f"<STORYBOARD_CREATED>{len(segments)} segments</STORYBOARD_CREATED>")
    await _sync_status(ctx, state, f"Storyboard created with {len(segments)} segments")

    # Send a message asking for approval
    await ctx.context.stream(
        ThreadItemDoneEvent(
            item=AssistantMessageItem(
                thread_id=ctx.context.thread.id,
                id=ctx.context.generate_id("message"),
                created_at=datetime.now(),
                content=[
                    AssistantMessageContent(
                        text=f"I've created a storyboard with {len(segments)} segments. Please review and let me know if you'd like any changes, or approve to proceed with video generation."
                    )
                ],
            ),
        )
    )


@function_tool(
    description_override=(
        "Approve the storyboard and start video generation.\n"
        "Call this after the user confirms they're happy with the storyboard."
    )
)
async def start_video_generation(
    ctx: RunContextWrapper[VideoAgentContext],
):
    """Start video generation after storyboard approval."""
    logger.info("[TOOL CALL] start_video_generation")

    def mutate(state: VideoProjectState) -> None:
        state.storyboard_approved = True
        state.phase = ProjectPhase.GENERATING
        state.touch()

    state = await _update_state(ctx, mutate)
    await _add_hidden_context(ctx, "<STORYBOARD_APPROVED></STORYBOARD_APPROVED>")
    await _add_hidden_context(ctx, "<VIDEO_GENERATION_STARTED></VIDEO_GENERATION_STARTED>")
    await _sync_status(ctx, state, "Video generation started")

    return {
        "status": "generation_started",
        "segments": len(state.segments),
        "message": "Video generation has begun. This may take a few minutes per segment.",
    }


@function_tool(
    description_override=(
        "Show video selection options for a specific segment.\n"
        "- `segment_id`: The ID of the segment to show options for\n"
        "- `video_urls`: List of video variant URLs to choose from"
    )
)
async def show_video_selection(
    ctx: RunContextWrapper[VideoAgentContext],
    segment_id: str,
    video_urls: List[str],
):
    """Display video selection widget for a segment."""
    logger.info("[TOOL CALL] show_video_selection for segment %s", segment_id)

    def mutate(state: VideoProjectState) -> None:
        for seg in state.segments:
            if seg.segment_id == segment_id:
                seg.video_variants = video_urls
                break
        state.phase = ProjectPhase.SELECTION
        state.touch()

    state = await _update_state(ctx, mutate)
    await _sync_status(ctx, state, f"Select video for segment {segment_id}")

    # Send a message with the selection options
    segment = next((s for s in state.segments if s.segment_id == segment_id), None)
    if segment:
        await ctx.context.stream(
            ThreadItemDoneEvent(
                item=AssistantMessageItem(
                    thread_id=ctx.context.thread.id,
                    id=ctx.context.generate_id("message"),
                    created_at=datetime.now(),
                    content=[
                        AssistantMessageContent(
                            text=f"Here are {len(video_urls)} options for segment '{segment.description[:50]}...'. Which one do you prefer?"
                        )
                    ],
                ),
            )
        )


@function_tool(
    description_override=(
        "Select a video variant for a segment.\n"
        "- `segment_id`: The segment ID\n"
        "- `variant_index`: The index of the selected variant (0-based)"
    )
)
async def select_video_variant(
    ctx: RunContextWrapper[VideoAgentContext],
    segment_id: str,
    variant_index: int,
):
    """Record the user's video variant selection."""
    logger.info("[TOOL CALL] select_video_variant: segment=%s, index=%d", segment_id, variant_index)

    def mutate(state: VideoProjectState) -> None:
        state.select_variant(segment_id, variant_index)

    state = await _update_state(ctx, mutate)
    await _add_hidden_context(ctx, f"<SEGMENT_SELECTED>{segment_id}:{variant_index}</SEGMENT_SELECTED>")
    await _sync_status(ctx, state, f"Selected variant {variant_index + 1} for segment {segment_id}")

    return {"status": "selected", "segment_id": segment_id, "variant_index": variant_index}


@function_tool(
    description_override=(
        "Display the final assembled video and outputs.\n"
        "- `video_url`: URL of the final assembled video\n"
        "- `thumbnail_url`: URL of the thumbnail image\n"
        "- `banner_url`: URL of the banner image\n"
        "- `marketing_copy`: Marketing copy text"
    )
)
async def show_final_output(
    ctx: RunContextWrapper[VideoAgentContext],
    video_url: str,
    thumbnail_url: str,
    banner_url: str,
    marketing_copy: str,
):
    """Display the final output to the user."""
    logger.info("[TOOL CALL] show_final_output")

    def mutate(state: VideoProjectState) -> None:
        state.set_final_output(video_url, thumbnail_url, banner_url, marketing_copy)

    state = await _update_state(ctx, mutate)
    await _add_hidden_context(ctx, "<PROJECT_COMPLETE></PROJECT_COMPLETE>")
    await _sync_status(ctx, state, "Project complete!")

    await ctx.context.stream(
        ThreadItemDoneEvent(
            item=AssistantMessageItem(
                thread_id=ctx.context.thread.id,
                id=ctx.context.generate_id("message"),
                created_at=datetime.now(),
                content=[
                    AssistantMessageContent(
                        text=f"Your video is ready!\n\n**Marketing Copy:**\n{marketing_copy}"
                    )
                ],
            ),
        )
    )


video_agent = Agent[VideoAgentContext](
    model=MODEL,
    model_settings=ModelSettings(reasoning=Reasoning(effort="high", summary="auto")),
    name="OvenAI Video Creator",
    instructions=INSTRUCTIONS,
    tools=[
        # Read state
        get_project_status,
        # Configure project
        set_project_details,
        # Storyboard creation
        create_storyboard,
        # Video generation
        start_video_generation,
        # Video selection
        show_video_selection,
        select_video_variant,
        # Final output
        show_final_output,
    ],
    # Stop inference after tool calls that produce widgets or require user input
    tool_use_behavior=StopAtTools(
        stop_at_tool_names=[
            create_storyboard.name,
            show_video_selection.name,
            show_final_output.name,
        ]
    ),
)
