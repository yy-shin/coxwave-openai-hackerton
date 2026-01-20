"""Helpers that convert ChatKit thread items into model-friendly inputs."""

from __future__ import annotations

from inspect import cleandoc

from agents import TResponseInputItem
from chatkit.agents import ThreadItemConverter
from chatkit.types import (
    Attachment,
    HiddenContextItem,
    UserMessageItem,
    UserMessageTagContent,
    UserMessageTextContent,
)
from openai.types.responses import ResponseInputContentParam, ResponseInputTextParam
from openai.types.responses.response_input_item_param import Message
from typing_extensions import assert_never

from .attachments import attachment_to_message_content, attachment_to_message_contents


class BasicThreadItemConverter(ThreadItemConverter):
    """Adds HiddenContextItem support and attachment path info for storyboard generation."""

    async def attachment_to_message_content(
        self, attachment: Attachment
    ) -> ResponseInputContentParam:
        return attachment_to_message_content(attachment)

    async def hidden_context_to_input(self, item: HiddenContextItem):
        return Message(
            type="message",
            content=[
                ResponseInputTextParam(
                    type="input_text",
                    text=item.content,
                )
            ],
            role="user",
        )

    async def user_message_to_input(
        self, item: UserMessageItem, is_last_message: bool = True
    ) -> TResponseInputItem | list[TResponseInputItem] | None:
        """Override to include attachment file paths in the message.

        This allows the agent to reference attached images by their local file paths
        when creating storyboards.
        """
        # Build the user text exactly as typed, rendering tags as @key
        message_text_parts: list[str] = []
        raw_tags: list[UserMessageTagContent] = []

        for part in item.content:
            if isinstance(part, UserMessageTextContent):
                message_text_parts.append(part.text)
            elif isinstance(part, UserMessageTagContent):
                message_text_parts.append(f"@{part.text}")
                raw_tags.append(part)
            else:
                assert_never(part)

        # Build attachment content parts (includes path info + actual content)
        attachment_parts: list[ResponseInputContentParam] = []
        for attachment in item.attachments:
            attachment_parts.extend(attachment_to_message_contents(attachment))

        user_text_item = Message(
            role="user",
            type="message",
            content=[
                ResponseInputTextParam(
                    type="input_text", text="".join(message_text_parts)
                ),
                *attachment_parts,
            ],
        )

        # Build system items (prepend later): quoted text and @-mention context
        context_items: list[TResponseInputItem] = []

        if item.quoted_text and is_last_message:
            context_items.append(
                Message(
                    role="user",
                    type="message",
                    content=[
                        ResponseInputTextParam(
                            type="input_text",
                            text=f"The user is referring to this in particular: \n{item.quoted_text}",
                        )
                    ],
                )
            )

        # Dedupe tags (preserve order) and resolve to message content
        if raw_tags:
            seen, uniq_tags = set(), []
            for t in raw_tags:
                if t.text not in seen:
                    seen.add(t.text)
                    uniq_tags.append(t)

            tag_content = [
                await self.tag_to_message_content(tag) for tag in uniq_tags
            ]

            if tag_content:
                context_items.append(
                    Message(
                        role="user",
                        type="message",
                        content=[
                            ResponseInputTextParam(
                                type="input_text",
                                text=cleandoc("""
                                    # User-provided context for @-mentions
                                    - When referencing resolved entities, use their canonical names **without** '@'.
                                    - The '@' form appears only in user text and should not be echoed.
                                """).strip(),
                            ),
                            *tag_content,
                        ],
                    )
                )

        return [user_text_item, *context_items]
