"""FastAPI entrypoint wiring the ChatKit server and REST endpoints."""

from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any

from chatkit.server import StreamingResult
from fastapi import Depends, FastAPI, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse, Response, StreamingResponse
from starlette.responses import JSONResponse

from .attachment_store import LocalAttachmentStore
from .server import CatAssistantServer, create_chatkit_server

# Initialize attachment store
UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
attachment_store = LocalAttachmentStore(
    upload_dir=str(UPLOAD_DIR),
    base_url="http://localhost:8001/uploads",
)

app = FastAPI(title="ChatKit API")

_chatkit_server: CatAssistantServer | None = create_chatkit_server(attachment_store)


def get_chatkit_server() -> CatAssistantServer:
    if _chatkit_server is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "ChatKit dependencies are missing. Install the ChatKit Python "
                "package to enable the conversational endpoint."
            ),
        )
    return _chatkit_server


@app.post("/chatkit")
async def chatkit_endpoint(
    request: Request, server: CatAssistantServer = Depends(get_chatkit_server)
) -> Response:
    payload = await request.body()
    result = await server.process(payload, {"request": request})
    if isinstance(result, StreamingResult):
        return StreamingResponse(result, media_type="text/event-stream")
    if hasattr(result, "json"):
        return Response(content=result.json, media_type="application/json")
    return JSONResponse(result)


@app.get("/cats/{thread_id}")
async def read_cat_state(
    thread_id: str,
    server: CatAssistantServer = Depends(get_chatkit_server),
) -> dict[str, Any]:
    state = await server.cat_store.load(thread_id)
    return {"cat": state.to_payload(thread_id)}


@app.post("/chatkit/upload/{attachment_id}")
async def upload_attachment(
    attachment_id: str,
    file: UploadFile,
) -> dict[str, str]:
    """Handle two-phase upload: receive file bytes and save to local storage."""
    attachment = attachment_store.get_attachment(attachment_id)
    if attachment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Attachment {attachment_id} not found",
        )

    # Determine file extension from mime type
    extension = mimetypes.guess_extension(attachment.mime_type) or ""
    file_path = attachment_store.get_file_path(attachment_id, extension)

    # Save file to disk
    content = await file.read()
    file_path.write_bytes(content)

    # Update attachment with file URL
    file_url = f"/uploads/{attachment_id}{extension}"
    attachment_store.update_attachment_after_upload(attachment_id, file_url)

    return {"status": "ok", "url": file_url}


@app.get("/uploads/{filename}")
async def serve_upload(filename: str) -> FileResponse:
    """Serve uploaded files."""
    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File {filename} not found",
        )

    mime_type, _ = mimetypes.guess_type(str(file_path))
    return FileResponse(file_path, media_type=mime_type or "application/octet-stream")
