"""Local file system attachment store for ChatKit."""

from __future__ import annotations

import logging
import mimetypes
import uuid
from pathlib import Path
from typing import Any

from chatkit.store import AttachmentStore

logger = logging.getLogger(__name__)
from chatkit.types import (
    Attachment,
    AttachmentCreateParams,
    AttachmentUploadDescriptor,
    FileAttachment,
    ImageAttachment,
)


class LocalAttachmentStore(AttachmentStore[dict[str, Any]]):
    """Store attachments in a local directory."""

    def __init__(
        self,
        upload_dir: str = "uploads",
        base_url: str = "http://localhost:8001/uploads",
    ) -> None:
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.base_url = base_url
        self._attachments: dict[str, Attachment] = {}

    def generate_attachment_id(self, mime_type: str, context: dict[str, Any]) -> str:
        return f"attachment_{uuid.uuid4().hex}"

    async def create_attachment(
        self, input: AttachmentCreateParams, context: dict[str, Any]
    ) -> Attachment:
        attachment_id = self.generate_attachment_id(input.mime_type, context)

        # Determine file extension and preview URL (use file:// for local paths)
        extension = mimetypes.guess_extension(input.mime_type) or ""
        file_path = self.upload_dir / f"{attachment_id}{extension}"
        preview_url = f"file://{file_path.absolute()}"

        # Create upload descriptor for two-phase upload
        upload_descriptor = AttachmentUploadDescriptor(
            url=f"http://localhost:8001/chatkit/upload/{attachment_id}",
            method="POST",
        )

        # Create attachment based on mime type
        if input.mime_type.startswith("image/"):
            attachment = ImageAttachment(
                id=attachment_id,
                name=input.name,
                mime_type=input.mime_type,
                upload_descriptor=upload_descriptor,
                preview_url=preview_url,
            )
        else:
            attachment = FileAttachment(
                id=attachment_id,
                name=input.name,
                mime_type=input.mime_type,
                upload_descriptor=upload_descriptor,
            )

        self._attachments[attachment_id] = attachment
        logger.info(f"Created attachment: {attachment.model_dump_json()}")
        return attachment

    async def delete_attachment(
        self, attachment_id: str, context: dict[str, Any]
    ) -> None:
        # Remove from memory
        if attachment_id in self._attachments:
            del self._attachments[attachment_id]

        # Remove file from disk
        for file_path in self.upload_dir.glob(f"{attachment_id}.*"):
            file_path.unlink(missing_ok=True)

    def get_attachment(self, attachment_id: str) -> Attachment | None:
        return self._attachments.get(attachment_id)

    def get_file_path(self, attachment_id: str, extension: str) -> Path:
        return self.upload_dir / f"{attachment_id}{extension}"

    def update_attachment_after_upload(
        self, attachment_id: str, file_url: str
    ) -> Attachment | None:
        attachment = self._attachments.get(attachment_id)
        if attachment is None:
            return None

        # Clear upload_descriptor after successful upload and set preview_url for images
        if isinstance(attachment, ImageAttachment):
            updated = ImageAttachment(
                id=attachment.id,
                name=attachment.name,
                mime_type=attachment.mime_type,
                upload_descriptor=None,
                preview_url=file_url,
            )
        else:
            updated = FileAttachment(
                id=attachment.id,
                name=attachment.name,
                mime_type=attachment.mime_type,
                upload_descriptor=None,
            )

        self._attachments[attachment_id] = updated
        return updated
