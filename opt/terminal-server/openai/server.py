import asyncio
import logging
import os
import pty
import pwd
import subprocess
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)


HOST = "0.0.0.0"
PORT = 1384


class OpenRequest(BaseModel):
\
\
\
\
\
\
\
       

    cmd: list[str]
    env: dict[str, str]
    user: str = ""
    cwd: str | None = None


class RawResponse(Response):
    media_type = "application/octet-stream"


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pipes = {}
    app.state.bearer_token = os.environ.get("BEARER_TOKEN")
    try:
        yield
    finally:
        for pipe in app.state.pipes.values():
            try:
                os.close(pipe)
            except Exception:
                pass


app = FastAPI(
    lifespan=lifespan,
)


EXCLUDE_BEARER_TOKEN_FROM_ROUTES = ["/healthcheck"]


@app.middleware("http")
async def verify_bearer_token(request: Request, call_next) -> Response:
    if request.url.path in EXCLUDE_BEARER_TOKEN_FROM_ROUTES:
        return await call_next(request)

    expected_bearer_token = app.state.bearer_token
    if expected_bearer_token and request.headers.get("authorization") != expected_bearer_token:
        return JSONResponse(status_code=401, content={"detail": "Invalid or missing bearer token"})

    return await call_next(request)


def get_env(request: OpenRequest) -> dict[str, str]:
                                                            
    env = os.environ.copy()
    env["HOME"] = os.path.expanduser(f"~{request.user or ''}")

                                                                      
    env.update(
        {
            "TERM": "vt100",
            "COLUMNS": "80",
            "LINES": "24",
            **request.env,
        }
    )

    return env


@app.get("/healthcheck")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/open")
async def open(request: OpenRequest) -> int:
                                                 
    master, slave = pty.openpty()
    os.set_blocking(master, False)

    if request.cwd and not os.path.isabs(request.cwd):
        raise HTTPException(
            status_code=400, detail=f"CWD must be an absolute path.  Received: '{request.cwd}'"
        )

    env = get_env(request)
    user = request.user or None

    if user:
        try:
            user_info = pwd.getpwnam(user)
            uid, gid = user_info.pw_uid, user_info.pw_gid
            os.chown(os.ttyname(slave), uid, gid)
        except Exception as e:
            logger.exception("Failed to chown slave")
            try:
                os.close(master)
                os.close(slave)
            except Exception:
                pass
            if isinstance(e, PermissionError):
                raise HTTPException(
                    status_code=400, detail=f"Failed to chown slave: {user=}"
                ) from e
            elif isinstance(e, KeyError):
                raise HTTPException(status_code=400, detail=f"User not found: {user}") from e
            else:
                raise e

    try:
                                                                             
        process = subprocess.Popen(
            request.cmd,
            stdin=slave,
            stdout=slave,
            stderr=slave,
            start_new_session=True,
            text=False,
            env=env,
            cwd=request.cwd,
            user=user,
        )
        os.close(slave)
    except Exception as e:
        logger.exception("Failed to open process")
        try:
            os.close(master)
            os.close(slave)
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=f"Failed to create process: {e}") from e
    app.state.pipes[process.pid] = master
    return process.pid


@app.post("/read/{pid}")
async def read(pid: int, request: Request) -> RawResponse:
    pipe = app.state.pipes.get(pid)
    if pipe is None:
        raise HTTPException(status_code=404, detail=f"Process not found: {pid}")
    else:
        try:
            size = int(await request.body())
            data = bytearray()
            try:
                while size > 0:
                    try:
                        await asyncio.sleep(0.1)
                        chunk = os.read(pipe, size)
                        if chunk:
                            size -= len(chunk)
                            data.extend(chunk)
                    except BlockingIOError:
                        break
            except Exception as e:
                if not data:
                    logger.exception("Failed to read from pipe")
                    raise HTTPException(status_code=409, detail=f"Failed to read: {e}") from e
            return RawResponse(content=bytes(data))
        except ValueError as e:
            logger.exception("Failed to parse size")
            raise HTTPException(status_code=400, detail=f"Failed to parse size: {e}") from e


@app.post("/write/{pid}")
async def write(pid: int, request: Request) -> int:
    pipe = app.state.pipes.get(pid)
    if pipe is None:
        raise HTTPException(status_code=404, detail=f"Process not found: {pid}")
    else:
        try:
            data = await request.body()
            size = os.write(pipe, data)
            return size
        except Exception as e:
            logger.exception("Failed to write to pipe")
            raise HTTPException(status_code=409, detail=f"Failed to write: {e}") from e


@app.post("/kill/{pid}")
async def close(pid: int) -> None:
    pipe = app.state.pipes.pop(pid, None)
    if pipe is None:
        raise HTTPException(status_code=404, detail=f"Process not found: {pid}")
    else:
        try:
            os.close(pipe)
        except Exception as e:
            logger.exception("Failed to close pipe")
            raise HTTPException(status_code=409, detail=f"Failed to close: {e}") from e


def main() -> None:
    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
    )


if __name__ == "__main__":
    main()
