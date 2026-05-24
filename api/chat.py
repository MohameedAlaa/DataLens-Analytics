from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, List

from backend.api_helpers import generate_chat_response

app = FastAPI()

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    question: str
    history: List[ChatMessage] = Field(default_factory=list)
    dataset: List[Dict[str, Any]]
    filename: str | None = None

@app.post('/')
async def chat(req: ChatRequest):
    if not req.dataset:
        raise HTTPException(status_code=400, detail='Dataset rows are required for chat requests')

    try:
        return generate_chat_response(req.question, [m.dict() for m in req.history], req.dataset, req.filename)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'Chat processing failed: {exc}') from exc
