"""
VideoAssistantServer implements the ChatKit server interface.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, AsyncIterator

from agents import Runner
from chatkit.agents import stream_agent_response
from chatkit.server import ChatKitServer
from chatkit.types import (
    Action,
    AssistantMessageContent,
    AssistantMessageItem,
    Attachment,
    HiddenContextItem,
    StreamOptions,
    ThreadItemDoneEvent,
    ThreadMetadata,
    ThreadStreamEvent,
    UserMessageItem,
    WidgetItem,
)
from openai.types.responses import ResponseInputContentParam

from .memory_store import MemoryStore
from .thread_item_converter import BasicThreadItemConverter
from .video_agent import VideoAgentContext, video_agent
from .video_project_store import VideoProjectStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VideoAssistantServer(ChatKitServer[dict[str, Any]]):
    """ChatKit server for video generation workflows."""

    def __init__(self) -> None:
        self.store: MemoryStore = MemoryStore()
        super().__init__(self.store)

        # Domain-specific store for video project state
        self.project_store = VideoProjectStore()
        self.thread_item_converter = BasicThreadItemConverter()

    async def action(
        self,
        thread: ThreadMetadata,
        action: Action[str, Any],
        sender: WidgetItem | None,
        context: dict[str, Any],
    ) -> AsyncIterator[ThreadStreamEvent]:
        """Handle widget actions like video selection and storyboard approval."""
        logger.info("[ACTION] type=%s", action.type)

        if action.type == "video.approve_storyboard":
            async for event in self._handle_approve_storyboard(thread, action.payload, sender, context):
                yield event
            return

        if action.type == "video.select_segment":
            async for event in self._handle_select_segment(thread, action.payload, sender, context):
                yield event
            return

        if action.type == "video.regenerate_segment":
            async for event in self._handle_regenerate_segment(thread, action.payload, sender, context):
                yield event
            return

        # Unknown action type
        logger.warning("[ACTION] Unknown action type: %s", action.type)
        return

    async def respond(
        self,
        thread: ThreadMetadata,
        item: UserMessageItem | None,
        context: dict[str, Any],
    ) -> AsyncIterator[ThreadStreamEvent]:
        """Run the video agent to respond to user messages."""
        logger.info("[RESPOND] thread_id=%s", thread.id)

        # Create agent context with access to stores
        agent_context = VideoAgentContext(
            thread=thread,
            store=self.store,
            projects=self.project_store,
            request_context=context,
        )

        # Load all items in the thread for context
        items_page = await self.store.load_thread_items(
            thread.id,
            after=None,
            limit=50,
            order="desc",
            context=context,
        )

        # Runner expects the most recent message to be last
        items = list(reversed(items_page.data))

        # Translate ChatKit thread items into agent input
        input_items = await self.thread_item_converter.to_agent_input(items)

        # Run the agent with streaming
        result = Runner.run_streamed(
            video_agent,
            input_items,
            context=agent_context,
        )

        # Stream agent response events
        async for event in stream_agent_response(agent_context, result):
            yield event

    def get_stream_options(self, thread: ThreadMetadata, context: dict[str, Any]) -> StreamOptions:
        """Configure streaming options."""
        # Don't allow stream cancellation as video operations may update state
        return StreamOptions(allow_cancel=False)

    async def to_message_content(self, _input: Attachment) -> ResponseInputContentParam:
        """Convert attachments to message content."""
        # TODO: Support file attachments for reference videos/images
        raise RuntimeError("File attachments are not yet supported.")

    # --- Private action handlers ---

    async def _handle_approve_storyboard(
        self,
        thread: ThreadMetadata,
        payload: dict[str, Any],
        sender: WidgetItem | None,
        context: dict[str, Any],
    ) -> AsyncIterator[ThreadStreamEvent]:
        """Handle storyboard approval action."""
        logger.info("[ACTION] approve_storyboard")

        state = await self.project_store.load(thread.id)

        def mutate(s):
            s.storyboard_approved = True
            s.phase = "generating"
            s.touch()

        state = await self.project_store.mutate(thread.id, mutate)

        # Add hidden context
        await self.store.add_thread_item(
            thread.id,
            HiddenContextItem(
                id=self.store.generate_item_id("message", thread, context),
                thread_id=thread.id,
                created_at=datetime.now(),
                content="<STORYBOARD_APPROVED></STORYBOARD_APPROVED>",
            ),
            context=context,
        )

        # Send confirmation message
        message_item = AssistantMessageItem(
            id=self.store.generate_item_id("message", thread, context),
            thread_id=thread.id,
            created_at=datetime.now(),
            content=[
                AssistantMessageContent(
                    text="Storyboard approved! Starting video generation..."
                )
            ],
        )
        yield ThreadItemDoneEvent(item=message_item)

    async def _handle_select_segment(
        self,
        thread: ThreadMetadata,
        payload: dict[str, Any],
        sender: WidgetItem | None,
        context: dict[str, Any],
    ) -> AsyncIterator[ThreadStreamEvent]:
        """Handle video segment selection action."""
        segment_id = payload.get("segment_id")
        variant_index = payload.get("variant_index", 0)
        logger.info("[ACTION] select_segment: %s -> %d", segment_id, variant_index)

        def mutate(s):
            s.select_variant(segment_id, variant_index)

        state = await self.project_store.mutate(thread.id, mutate)

        # Add hidden context
        await self.store.add_thread_item(
            thread.id,
            HiddenContextItem(
                id=self.store.generate_item_id("message", thread, context),
                thread_id=thread.id,
                created_at=datetime.now(),
                content=f"<SEGMENT_SELECTED>{segment_id}:{variant_index}</SEGMENT_SELECTED>",
            ),
            context=context,
        )

        # Send confirmation message
        message_item = AssistantMessageItem(
            id=self.store.generate_item_id("message", thread, context),
            thread_id=thread.id,
            created_at=datetime.now(),
            content=[
                AssistantMessageContent(
                    text=f"Selected variant {variant_index + 1} for segment {segment_id}."
                )
            ],
        )
        yield ThreadItemDoneEvent(item=message_item)

    async def _handle_regenerate_segment(
        self,
        thread: ThreadMetadata,
        payload: dict[str, Any],
        sender: WidgetItem | None,
        context: dict[str, Any],
    ) -> AsyncIterator[ThreadStreamEvent]:
        """Handle segment regeneration request."""
        segment_id = payload.get("segment_id")
        logger.info("[ACTION] regenerate_segment: %s", segment_id)

        # Add hidden context
        await self.store.add_thread_item(
            thread.id,
            HiddenContextItem(
                id=self.store.generate_item_id("message", thread, context),
                thread_id=thread.id,
                created_at=datetime.now(),
                content=f"<REGENERATE_SEGMENT>{segment_id}</REGENERATE_SEGMENT>",
            ),
            context=context,
        )

        # Send confirmation message
        message_item = AssistantMessageItem(
            id=self.store.generate_item_id("message", thread, context),
            thread_id=thread.id,
            created_at=datetime.now(),
            content=[
                AssistantMessageContent(
                    text=f"Regenerating video for segment {segment_id}..."
                )
            ],
        )
        yield ThreadItemDoneEvent(item=message_item)


def create_chatkit_server() -> VideoAssistantServer | None:
    """Return a configured ChatKit server instance."""
    return VideoAssistantServer()
