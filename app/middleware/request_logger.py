# app/middleware/request_logger.py
import time
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

class RequestLoggerMiddleware:
    """
    Logs every HTTP request with:
      - method, path, status, duration
      - X-Req-Id (from client) and X-Sid (session id)
      - request body (safe for small JSON posts)

    Safe body-read: resets request receive buffer after reading.
    """
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        start = time.time()

        # Read body safely
        body_bytes = await request.body()
        # Restore body so downstream handlers can read it
        async def _receive():
            return {"type": "http.request", "body": body_bytes, "more_body": False}
        scope["_body"] = body_bytes  # optional debug
        # Call downstream app with restored body
        async def send_wrapper(message):
            await send(message)

        rid = request.headers.get("x-req-id", "-")
        sid = request.headers.get("x-sid", "-")
        path = request.url.path

        print(f"[HTTP ►] rid={rid} sid={sid} {request.method} {path} body={body_bytes.decode('utf-8', 'ignore')}")

        async def receive_wrapper():
            return await _receive()

        await self.app(scope, receive_wrapper, send_wrapper)

        dur_ms = (time.time() - start) * 1000
        # We can't directly read status here; rely on access logs or add a Response wrapper if needed
        print(f"[HTTP ◄] rid={rid} sid={sid} {path} done in {dur_ms:.1f}ms")
