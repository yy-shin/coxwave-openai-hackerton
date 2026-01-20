"""Video generation agent with ChatKit integration."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated, Any, Callable, List

from agents import (
    Agent,
    GuardrailFunctionOutput,
    ModelSettings,
    Runner,
    RunContextWrapper,
    StopAtTools,
    TResponseInputItem,
    function_tool,
    input_guardrail,
)
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

from .video_project_state import GenerationInput, Segment, VideoProjectState
from .video_project_store import VideoProjectStore


class GenerationInputData(BaseModel):
    """Input model for a generation provider configuration."""

    provider: str = Field(description="Video generation provider ('veo', 'sora')")
    prompt: str = Field(description="The prompt for video generation")
    negative_prompt: str | None = Field(
        default=None, description="Negative prompt to avoid certain elements"
    )
    reference_image_paths: List[str] = Field(
        default_factory=list, description="List of local file paths to reference images"
    )
    input_image_path: str | None = Field(
        default=None, description="Local file path to input image for image-to-video"
    )


class SegmentInput(BaseModel):
    """Input model for a storyboard segment."""

    scene_description: str = Field(description="What happens in this segment")
    duration: float = Field(default=8.0, description="Duration in seconds")
    generation_inputs: List[GenerationInputData] = Field(
        description="List of generation configurations for different providers"
    )


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

INSTRUCTIONS: str = """
You are OvenAI, an expert video advertisement creation assistant helping users create
high-quality marketing videos for games and products.

## Workflow
1. **Clarifying**: Ask clarifying questions to understand:
   - What product/game is being advertised
   - Target audience and platform
   - Desired tone and style
   - Key selling points to highlight
   - Reference materials (videos, images)
   - Aspect ratio (default: 9:16 portrait)
   - Target duration (default: 30 seconds, max: 60 seconds)

2. **Storyboard**: Once you have enough information:
   - Create a detailed storyboard with 4-8 segments
   - Each segment should be 3-8 seconds
   - Call `create_storyboard` to display the visual storyboard
   - Wait for user approval before proceeding

3. **Generation**: After approval:
   - Generate keyframe images for each segment
   - Select appropriate video model for each segment:
     - Sora: realistic/cinematic footage
     - Veo: stylized/artistic content
   - Call `start_video_generation` to begin the process

## Tools
- `get_project_status`: Check current project state before deciding what to do
- `set_project_details`: Set project title, aspect ratio, duration, and description
- `create_storyboard`: Create and display storyboard with segments
- `edit_storyboard_segment`: Edit a single segment by index (0-based) when user requests changes
- `start_video_generation`: Start video generation after storyboard approval

## Using Attached Images
When users attach images, you will see them in the conversation with their file paths like:
`[Attached file: image.png, path: /path/to/attachments/abc123_image.png]`

**IMPORTANT**: When creating a storyboard, use attached images in your generation inputs:
- Extract the `path` value from the attachment info (e.g., `/path/to/attachments/abc123_image.png`)
- Analyze the attached images to understand characters, style, and visual elements
- Reference these visual elements in your prompts for consistency

**Image Usage Options:**
1. `input_image_path` (image-to-video): Use when the video should START from this exact image
   - The first frame will be the attached image, then animated
   - Best for: animating a specific scene, character pose, or keyframe

2. `reference_image_paths` (style/character reference): Use for visual guidance
   - Model uses these to understand appearance/style but doesn't start from them
   - Best for: maintaining character consistency, art style, color palette

Example with attached image at `/data/attachments/abc_scene.png`:
```json
{
  "generation_inputs": [{
    "provider": "sora",
    "prompt": "The scene comes alive as the character begins to move...",
    "input_image_path": "/data/attachments/abc_scene.png",
    "reference_image_paths": []
  }]
}
```

Example using image as reference only:
```json
{
  "generation_inputs": [{
    "provider": "sora",
    "prompt": "A similar character walks through a forest...",
    "input_image_path": null,
    "reference_image_paths": ["/data/attachments/abc_character.png"]
  }]
}
```

## Important Notes
- Keep responses concise and professional
- Always confirm understanding before proceeding to next step
- Video models: Sora (realistic/cinematic), Veo (stylized/artistic)
- Once an action has been performed, it will be reflected as a tag in the thread content:
  - <STORYBOARD_CREATED>: Storyboard was created
  - <STORYBOARD_APPROVED>: User approved storyboard
  - <VIDEO_GENERATION_STARTED>: Video generation began

## CRITICAL: State Synchronization
- **ALWAYS call `get_project_status` before creating or editing the storyboard.**
- Users can edit storyboard content directly via the UI, so the state may have changed since your last action.
- Failure to read current state first may cause data corruption or overwrite user edits.
- This rule must be followed at all times without exception.
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


async def _add_hidden_context(
    ctx: RunContextWrapper[VideoAgentContext], content: str
) -> None:
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


@function_tool(description_override="Get the current project status. No parameters.")
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
        "- `total_duration`: Target video duration in seconds (max 60)\n"
        "- `description`: Brief description of the video concept"
    )
)
async def set_project_details(
    ctx: RunContextWrapper[VideoAgentContext],
    title: str | None = None,
    aspect_ratio: str | None = None,
    total_duration: int | None = None,
    description: str | None = None,
):
    """Set project configuration details."""
    logger.info("[TOOL CALL] set_project_details")

    def mutate(state: VideoProjectState) -> None:
        if title:
            state.title = title
        if aspect_ratio:
            state.aspect_ratio = aspect_ratio
        if total_duration:
            state.total_duration = min(total_duration, 60)
        if description:
            state.description = description
        state.touch()

    state = await _update_state(ctx, mutate)

    # Update thread title
    if title:
        ctx.context.thread.title = title
        await ctx.context.store.save_thread(
            ctx.context.thread, ctx.context.request_context
        )

    await _sync_status(ctx, state, f"Project updated: {state.title}")
    return state.to_payload(ctx.context.thread.id)


@function_tool(
    description_override=(
        "Create and display a storyboard for the video.\n"
        "- `segments`: List of segment objects with scene_description, duration, and generation_inputs"
    )
)
async def create_storyboard(
    ctx: RunContextWrapper[VideoAgentContext],
    segments: List[SegmentInput],
):
    """Create a storyboard and display it to the user."""
    logger.info("[TOOL CALL] create_storyboard with %d segments", len(segments))

    from .video_project_state import ImageInput

    storyboard_segments = [
        Segment(
            scene_description=seg.scene_description,
            duration=seg.duration,
            generation_inputs=[
                GenerationInput(
                    provider=gi.provider,  # type: ignore[arg-type]
                    prompt=gi.prompt,
                    negative_prompt=gi.negative_prompt,
                    reference_images=(
                        [ImageInput(file_path=path) for path in gi.reference_image_paths]
                        if gi.reference_image_paths
                        else None
                    ),
                    input_image=(
                        ImageInput(file_path=gi.input_image_path)
                        if gi.input_image_path
                        else None
                    ),
                )
                for gi in seg.generation_inputs
            ],
        )
        for seg in segments
    ]

    def mutate(state: VideoProjectState) -> None:
        state.set_storyboard(storyboard_segments)

    state = await _update_state(ctx, mutate)
    await _add_hidden_context(
        ctx, f"<STORYBOARD_CREATED>{len(segments)} segments</STORYBOARD_CREATED>"
    )
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
        "Edit a single segment in the storyboard by index.\n"
        "- `segment_index`: The 0-based index of the segment to edit\n"
        "- `segment`: The updated segment with scene_description, duration, and generation_inputs"
    )
)
async def edit_storyboard_segment(
    ctx: RunContextWrapper[VideoAgentContext],
    segment_index: int,
    segment: SegmentInput,
):
    """Edit a single segment in the storyboard."""
    logger.info("[TOOL CALL] edit_storyboard_segment: index=%d", segment_index)

    state = await _get_state(ctx)

    # Validate segment index
    if segment_index < 0 or segment_index >= len(state.storyboard.segments):
        return {
            "status": "error",
            "message": f"Invalid segment index {segment_index}. Storyboard has {len(state.storyboard.segments)} segments (0-{len(state.storyboard.segments) - 1}).",
        }

    from .video_project_state import ImageInput

    # Convert SegmentInput to Segment
    updated_segment = Segment(
        scene_description=segment.scene_description,
        duration=segment.duration,
        generation_inputs=[
            GenerationInput(
                provider=gi.provider,  # type: ignore[arg-type]
                prompt=gi.prompt,
                negative_prompt=gi.negative_prompt,
                reference_images=(
                    [ImageInput(file_path=path) for path in gi.reference_image_paths]
                    if gi.reference_image_paths
                    else None
                ),
                input_image=(
                    ImageInput(file_path=gi.input_image_path)
                    if gi.input_image_path
                    else None
                ),
            )
            for gi in segment.generation_inputs
        ],
    )

    def mutate(state: VideoProjectState) -> None:
        state.update_segment(segment_index, updated_segment)

    state = await _update_state(ctx, mutate)
    await _add_hidden_context(ctx, f"<SEGMENT_EDITED>{segment_index}</SEGMENT_EDITED>")
    await _sync_status(ctx, state, f"Segment {segment_index + 1} updated")

    return {
        "status": "success",
        "segment_index": segment_index,
        "message": f"Segment {segment_index + 1} has been updated.",
    }


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
        state.touch()

    state = await _update_state(ctx, mutate)
    await _add_hidden_context(ctx, "<STORYBOARD_APPROVED></STORYBOARD_APPROVED>")
    await _add_hidden_context(
        ctx, "<VIDEO_GENERATION_STARTED></VIDEO_GENERATION_STARTED>"
    )
    await _sync_status(ctx, state, "Video generation started")

    # Send client effect to frontend to trigger video generation API calls
    await ctx.context.stream(
        ClientEffectEvent(
            name="start_video_generation",
            data={"state": state.to_payload(ctx.context.thread.id)},
        )
    )

    return {
        "status": "generation_started",
        "segments": len(state.storyboard.segments),
        "message": "Video generation has begun. This may take a few minutes per segment.",
    }


video_agent = Agent[VideoAgentContext](
    model=MODEL,
    model_settings=ModelSettings(reasoning=Reasoning(effort="high", summary="auto")),
    name="OvenAI Video Creator",
    instructions=INSTRUCTIONS,
    tools=[
        get_project_status,
        set_project_details,
        create_storyboard,
        edit_storyboard_segment,
        start_video_generation,
    ],
    # Stop inference after tool calls that produce widgets or require user input
    tool_use_behavior=StopAtTools(
        stop_at_tool_names=[
            create_storyboard.name,
        ]
    ),
)
