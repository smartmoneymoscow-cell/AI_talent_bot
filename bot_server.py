"""
Bot + health check server for Render free tier.
Render expects web services to respond to HTTP health checks.
This runs both the bot (polling) and a tiny HTTP server.
"""
import asyncio
import os
import sys

from aiohttp import web

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai_talent_bot.main import main as run_bot


async def health_server():
    """Tiny HTTP server for Render health check."""
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="🤖 AI Talent Hub Bot — running"))
    app.router.add_get("/health", lambda r: web.Response(text="ok"))
    
    port = int(os.environ.get("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Health server on port {port}")


async def combined():
    """Run bot and health server together."""
    await health_server()
    await run_bot()


if __name__ == "__main__":
    asyncio.run(combined())
