import os
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncio

app = FastAPI()

# 读取人设
try:
    with open("system_prompt.txt", "r", encoding="utf-8") as f:
        SYSTEM_PROMPT = f.read()
except:
    SYSTEM_PROMPT = "你是一个有用的AI助手。"

API_KEY = os.getenv("API_KEY", "")
API_BASE_URL = os.getenv("API_BASE_URL", "https://openrouter.ai/api/v1")

class ChatRequest(BaseModel):
    messages: list
    model: str
    stream: bool = False

@app.get("/v1/models")
async def get_models(request: Request):
    auth = request.headers.get("X-Gateway-Key")
    if auth != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{API_BASE_URL}/models",
            headers={"Authorization": f"Bearer {API_KEY}"}
        )
        return resp.json()

@app.post("/v1/chat/completions")
async def chat(request: Request, body: ChatRequest):
    auth = request.headers.get("X-Gateway-Key")
    if auth != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # 注入人设
    if body.messages and body.messages[0].get("role") == "system":
        # 如果已经有system消息，替换
        body.messages[0]["content"] = SYSTEM_PROMPT + "\n\n" + body.messages[0]["content"]
    else:
        body.messages.insert(0, {"role": "system", "content": SYSTEM_PROMPT})
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        if body.stream:
            return StreamingResponse(
                client.stream(
                    "POST",
                    f"{API_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json=body.dict()
                ),
                media_type="text/event-stream"
            )
        else:
            resp = await client.post(
                f"{API_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json"
                },
                json=body.dict()
            )
            return resp.json()
