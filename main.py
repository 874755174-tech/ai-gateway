import os
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

app = FastAPI()

# 读取人设
try:
    with open("system_prompt.txt", "r", encoding="utf-8") as f:
        SYSTEM_PROMPT = f.read()
except:
    SYSTEM_PROMPT = "你是一个有用的AI助手。"

# 两个独立的密钥
GATEWAY_KEY = os.getenv("GATEWAY_KEY", "")          # 客户端连接网关用
UPSTREAM_API_KEY = os.getenv("UPSTREAM_API_KEY", "") # 转发给上游AI用
API_BASE_URL = os.getenv("API_BASE_URL", "https://openrouter.ai/api/v1")

class ChatRequest(BaseModel):
    messages: list
    model: str
    stream: bool = False

@app.get("/v1/models")
async def get_models(request: Request):
    auth = request.headers.get("X-Gateway-Key")
    if auth != GATEWAY_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{API_BASE_URL}/models",
            headers={"Authorization": f"Bearer {UPSTREAM_API_KEY}"}  # 用上游密钥
        )
        return resp.json()

@app.post("/v1/chat/completions")
async def chat(request: Request, body: ChatRequest):
    auth = request.headers.get("X-Gateway-Key")
    if auth != GATEWAY_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # 注入人设
    if body.messages and body.messages[0].get("role") == "system":
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
                        "Authorization": f"Bearer {UPSTREAM_API_KEY}",  # 用上游密钥
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
                    "Authorization": f"Bearer {UPSTREAM_API_KEY}",  # 用上游密钥
                    "Content-Type": "application/json"
                },
                json=body.dict()
            )
            return resp.json()
