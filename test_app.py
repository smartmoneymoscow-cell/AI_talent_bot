"""Minimal test app for Render deployment."""
import os
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"status": "ok", "message": "AI Talent Hub is running!"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
