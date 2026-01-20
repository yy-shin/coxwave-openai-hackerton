"""Helpers for working with ChatKit attachments."""

from __future__ import annotations

import base64
from pathlib import Path

from chatkit.types import Attachment, ImageAttachment
from openai.types.responses import ResponseInputContentParam, ResponseInputFileParam
from openai.types.responses import ResponseInputImageParam, ResponseInputTextParam


def _read_attachment_bytes(attachment: Attachment) -> bytes:
    metadata = attachment.metadata or {}
    path = metadata.get("path")
    if not path:
        raise RuntimeError(f"Attachment {attachment.id} has no stored path")
    return Path(path).read_bytes()


def _get_attachment_path(attachment: Attachment) -> str | None:
    """Get the local file path from attachment metadata."""
    metadata = attachment.metadata or {}
    return metadata.get("path")


def attachment_to_message_contents(
    attachment: Attachment,
) -> list[ResponseInputContentParam]:
    """Convert an attachment into Responses API input content parts.

    Returns a list containing:
    - A text part with file path info (so agent can reference the file)
    - The actual file/image content
    """
    raw = _read_attachment_bytes(attachment)
    encoded = base64.b64encode(raw).decode("ascii")
    path = _get_attachment_path(attachment)

    parts: list[ResponseInputContentParam] = []

    # Add path info as text so agent knows how to reference it in storyboard
    if path:
        parts.append(
            ResponseInputTextParam(
                type="input_text",
                text=f"[Attached file: {attachment.name}, path: {path}]",
            )
        )

    if isinstance(attachment, ImageAttachment):
        parts.append(
            ResponseInputImageParam(
                type="input_image",
                detail="auto",
                image_url=f"data:{attachment.mime_type};base64,{encoded}",
            )
        )
    else:
        parts.append(
            ResponseInputFileParam(
                type="input_file",
                file_data=encoded,
                filename=attachment.name,
            )
        )

    return parts


def attachment_to_message_content(attachment: Attachment) -> ResponseInputContentParam:
    """Convert an attachment into a single Responses API input content part.

    Note: This doesn't include path info. Use attachment_to_message_contents()
    if you need the path for the agent to reference.
    """
    raw = _read_attachment_bytes(attachment)
    encoded = base64.b64encode(raw).decode("ascii")

    if isinstance(attachment, ImageAttachment):
        return ResponseInputImageParam(
            type="input_image",
            detail="auto",
            image_url=f"data:{attachment.mime_type};base64,{encoded}",
        )

    return ResponseInputFileParam(
        type="input_file",
        file_data=encoded,
        filename=attachment.name,
    )
