"""Local attachment storage for ChatKit uploads."""

from __future__ import annotations

import mimetypes
import os
from pathlib import Path
from typing import Any

from chatkit.store import AttachmentStore
from chatkit.types import (
    Attachment,
    AttachmentCreateParams,
    AttachmentUploadDescriptor,
    FileAttachment,
    ImageAttachment,
)

from .memory_store import MemoryStore


class LocalAttachmentStore(AttachmentStore[dict[str, Any]]):
    """Save attachments on disk and return local upload/preview URLs."""

    def __init__(self, store: MemoryStore, base_dir: Path) -> None:
        self.store = store
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def create_attachment(
        self, input: AttachmentCreateParams, context: dict[str, Any]
    ) -> Attachment:
        attachment_id = self.generate_attachment_id(input.mime_type, context)
        filename = os.path.basename(input.name) or "attachment"
        path = self.base_dir / f"{attachment_id}_{filename}"
        mime_type = input.mime_type or ""
        if not mime_type or mime_type == "application/octet-stream":
            guessed, _ = mimetypes.guess_type(filename)
            if guessed:
                mime_type = guessed
        # Upload URL uses local backend (frontend can access localhost)
        # Preview URL uses PUBLIC_URL for ChatKit iframe (requires public HTTPS)
        upload_url = self._build_local_url(context, f"/attachments/{attachment_id}/upload")
        preview_url = self._build_public_url(context, f"/attachments/{attachment_id}")
        upload_descriptor = AttachmentUploadDescriptor(
            url=upload_url,
            method="PUT",
            headers={"Content-Type": mime_type or "application/octet-stream"},
        )
        metadata = {"path": str(path), "size": input.size}

        if mime_type.startswith("image/"):
            attachment: Attachment = ImageAttachment(
                id=attachment_id,
                name=filename,
                mime_type=mime_type,
                upload_descriptor=upload_descriptor,
                preview_url=preview_url,
                metadata=metadata,
            )
        else:
            attachment = FileAttachment(
                id=attachment_id,
                name=filename,
                mime_type=mime_type or "application/octet-stream",
                upload_descriptor=upload_descriptor,
                metadata=metadata,
            )

        # Save to store so save_upload can find it later
        await self.store.save_attachment(attachment, context=context)
        return attachment

    async def delete_attachment(self, attachment_id: str, context: dict[str, Any]) -> None:
        attachment = await self.store.load_attachment(attachment_id, context=context)
        path = (attachment.metadata or {}).get("path")
        if path and Path(path).exists():
            Path(path).unlink(missing_ok=True)

    async def save_upload(
        self, attachment_id: str, data: bytes, context: dict[str, Any]
    ) -> Attachment:
        attachment = await self.store.load_attachment(attachment_id, context=context)
        path = (attachment.metadata or {}).get("path")
        if not path:
            raise RuntimeError(f"Attachment {attachment_id} has no storage path")
        Path(path).write_bytes(data)
        updated = attachment.model_copy(update={"upload_descriptor": None})
        await self.store.save_attachment(updated, context=context)
        return updated

    def _build_local_url(self, context: dict[str, Any], path: str) -> str:
        """Build URL using request origin (for uploads from frontend)."""
        request = context.get("request")
        if request is None:
            raise RuntimeError("Request context is required to build attachment URLs")
        base = str(request.base_url).rstrip("/")
        return f"{base}{path}"

    def _build_public_url(self, context: dict[str, Any], path: str) -> str:
        """Build URL using PUBLIC_URL env var (for ChatKit iframe previews)."""
        public_url = os.environ.get("PUBLIC_URL")
        if public_url:
            return f"{public_url.rstrip('/')}{path}"
        # Fall back to local URL if no PUBLIC_URL set
        return self._build_local_url(context, path)
