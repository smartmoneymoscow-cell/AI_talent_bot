FROM python:3.11-slim
WORKDIR /app
RUN pip install fastapi uvicorn aiosqlite python-dotenv aiohttp
COPY . .
WORKDIR /app/mini_app/backend
RUN mkdir -p data
CMD python3 -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
