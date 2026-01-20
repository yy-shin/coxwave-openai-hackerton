"""FastAPI entrypoint wiring the ChatKit server and REST endpoints."""

from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

import uuid
from pathlib import Path
from typing import Any

from chatkit.server import StreamingResult
from chatkit.store import NotFoundError
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
from starlette.responses import JSONResponse

from .server import VideoAssistantServer, create_chatkit_server
from .tools.video_generations import (
    VideoGenerations,
    generate_videos_from_project,
    get_video_local_path,
    poll_and_save_video_generations,
)
from .video_project_state import VideoProjectState

# Project root for storing generated videos
_PROJECT_ROOT = Path(__file__).parent.parent

app = FastAPI(title="OvenAI Video Generation API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_chatkit_server: VideoAssistantServer | None = create_chatkit_server()


def get_chatkit_server() -> VideoAssistantServer:
    """Dependency to get the ChatKit server instance."""
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
    request: Request, server: VideoAssistantServer = Depends(get_chatkit_server)
) -> Response:
    """ChatKit streaming endpoint for chat interactions."""
    payload = await request.body()
    result = await server.process(payload, {"request": request})
    if isinstance(result, StreamingResult):
        return StreamingResponse(result, media_type="text/event-stream")
    if hasattr(result, "json"):
        return Response(content=result.json, media_type="application/json")
    return JSONResponse(result)


@app.get("/projects/{thread_id}")
async def read_project_state(
    thread_id: str,
    server: VideoAssistantServer = Depends(get_chatkit_server),
) -> dict[str, Any]:
    """Get video project state for a thread."""
    state = await server.project_store.load(thread_id)
    return {"project": state.to_payload(thread_id)}


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.put("/attachments/{attachment_id}/upload")
async def upload_attachment(
    attachment_id: str,
    request: Request,
    server: VideoAssistantServer = Depends(get_chatkit_server),
) -> dict[str, str]:
    """Upload attachment bytes for two-phase upload."""
    data = await request.body()
    if not data:
        raise HTTPException(status_code=400, detail="Empty upload body")
    attachment_store = server._get_attachment_store()
    try:
        await attachment_store.save_upload(attachment_id, data, {"request": request})
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "ok"}


@app.get("/attachments/{attachment_id}")
async def read_attachment(
    attachment_id: str,
    request: Request,
    server: VideoAssistantServer = Depends(get_chatkit_server),
) -> Response:
    """Serve uploaded attachments for UI previews."""
    try:
        attachment = await server.store.load_attachment(
            attachment_id, context={"request": request}
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    path = (attachment.metadata or {}).get("path")
    if not path:
        raise HTTPException(status_code=404, detail="Attachment has no file path")
    return FileResponse(path, media_type=attachment.mime_type, filename=attachment.name)


@app.post("/generate")
async def submit_generation(state: VideoProjectState) -> VideoGenerations:
    """Submit a video generation request.

    Receives a VideoProjectState with a storyboard containing segments,
    and initiates video generation for each segment's generation inputs.

    Returns VideoGenerations with video IDs and initial status.
    """
    project_id = str(uuid.uuid4())
    return await generate_videos_from_project(project_id, state)


@app.post("/generate/status")
async def poll_generation_status(generations: VideoGenerations) -> VideoGenerations:
    """Poll for updated status of video generations.

    Receives a VideoGenerations object containing video IDs and providers,
    and returns an updated VideoGenerations with latest status/progress/URLs.
    Downloads completed videos to local storage.
    """
    return await poll_and_save_video_generations(generations, _PROJECT_ROOT)


@app.get("/videos/{project_id}/{segment_index}/{input_index}/{video_id}")
async def serve_video(
    project_id: str,
    segment_index: int,
    input_index: int,
    video_id: str,
) -> FileResponse:
    """Serve a generated video file."""
    file_path = get_video_local_path(
        _PROJECT_ROOT, project_id, segment_index, input_index, video_id
    )

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video not found: {video_id}",
        )

    return FileResponse(file_path, media_type="video/mp4")
