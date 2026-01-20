"""FastAPI entrypoint wiring the ChatKit server and REST endpoints."""

from __future__ import annotations

from typing import Any

from chatkit.server import StreamingResult
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import Response, StreamingResponse
from starlette.responses import JSONResponse

from .server import VideoAssistantServer, create_chatkit_server

app = FastAPI(title="OvenAI Video Generation API")

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
