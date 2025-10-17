from fastapi import FastAPI
import asyncio
from pydantic import BaseModel
from src.underthehood import process_task
import os

app=FastAPI()

key=os.getenv("secret_key")

class Request(BaseModel):
    email: str
    secret: str
    task: str
    round: int
    nonce: str
    brief: str
    checks: list[str]
    evaluation_url: str
    attachments: list[dict]

@app.get("/")
async def root():
    return {"message": "API is running"}


@app.post("/api-endpoint")
async def main(request: Request):
    if request.secret != key:
        return {"message": "permission Denied"}, 403
    # schedule background processing and return immediately
    asyncio.create_task(process_task(request.dict()))
    return {"message": "Accepted"}
