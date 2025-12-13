import asyncio
import logging
import os
import time
from collections import deque
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from jupyter_client.asynchronous.client import AsyncKernelClient
from jupyter_client.manager import AsyncKernelManager, start_new_async_kernel

from research_ace.v2.ace_types.errors import UserMachineResponseTooLarge
from research_ace.v2.ace_types.jupyter_message import IOPubMessage, parse_obj_as_io_pub_message
from research_ace.v2.ace_types.jupyter_server_types import (
    CallbackRequest,
    ExecuteError,
    ExecuteRequest,
    ExecuteResponse,
    GetStatusResponse,
    JupyterKernelStatus,
    LogExceptionRequest,
    LogMatplotlibFallbackRequest,
    PullMessageRequest,
    PullMessageResponse,
    RecordedCallback,
)

logger = logging.getLogger(__name__)

os.chdir(os.path.expanduser("~"))

_MAX_JUPYTER_MESSAGE_SIZE = 10 * 1024 * 1024

_kernel_restart_lock = asyncio.Lock()


                               
async def _create_kernel() -> tuple[AsyncKernelManager, AsyncKernelClient]:
    start_time = time.monotonic()
    logger.info("Starting kernel creation")
    try:
        km, kc = await start_new_async_kernel(startup_timeout=120.0)

        kc.log = logger
        logger.info(
            f"Kernel {km.kernel_id} created successfully after {(time.monotonic() - start_time):.3f}s"
        )
        return km, kc
    except Exception as e:
        logger.error(
            f"Kernel creation failed after {(time.monotonic() - start_time):.3f}s: {e}",
            exc_info=True,
        )
        await asyncio.sleep(5)
        raise


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    while True:
        try:
            app.state.callback_lock = asyncio.Lock()
            app.state.bearer_token = os.environ.get("BEARER_TOKEN")
            app.state.recorded_callbacks = deque(maxlen=_CALLBACK_RECORD_LIMIT)
            app.state.kernel_manager, app.state.kernel_client = await _create_kernel()
            break
        except Exception as e:
            logger.exception("Error creating kernel: %s", str(e))

    yield

    logger.info("Shutting down the user machine.")


app = FastAPI(lifespan=lifespan)

EXCLUDE_BEARER_TOKEN_FROM_ROUTES = ["/status"]


@app.middleware("http")
async def verify_bearer_token(request: Request, call_next) -> Response:
    if request.url.path in EXCLUDE_BEARER_TOKEN_FROM_ROUTES:
        return await call_next(request)

    expected_bearer_token = app.state.bearer_token
    if expected_bearer_token and request.headers.get("authorization") != expected_bearer_token:
        return JSONResponse(status_code=401, content={"detail": "Invalid or missing bearer token"})

    return await call_next(request)


                                   
_ALLOWED_CALLBACKS = {
    "display_dataframe_to_user",
    "display_chart_to_user",
    "display_matplotlib_image_to_user",
}
                                                               
_CALLBACK_RECORD_LIMIT = int(os.getenv("CALLBACK_RECORD_LIMIT", "1000"))
                                                                 
_CALLBACK_PULL_LIMIT = int(os.getenv("CALLBACK_PULL_LIMIT", "100"))


async def _get_kernel_status() -> JupyterKernelStatus:
    kc: AsyncKernelClient = app.state.kernel_client
    if kc is None:
        return JupyterKernelStatus.STARTING

    if _kernel_restart_lock.locked():
        return JupyterKernelStatus.RESTARTING

    if not await kc.is_alive():
        return JupyterKernelStatus.DEAD
    return JupyterKernelStatus.RUNNING


@app.get("/status")
async def get_status() -> GetStatusResponse:
    return GetStatusResponse(
        kernel_status=await _get_kernel_status(),
        version=os.environ.get("VM_BUILD", "unknown"),
    )


@app.post("/reset_kernel")
async def reset_kernel() -> JSONResponse:
    logger.info("Resetting kernel.")
    status = await _get_kernel_status()
    if status == JupyterKernelStatus.STARTING:
        return JSONResponse(status_code=503, content={"error": "Kernel is being created."})

    if status == JupyterKernelStatus.RESTARTING:
        return JSONResponse(status_code=503, content={"error": "Kernel is being restarted."})

    async with _kernel_restart_lock:
        try:
            km: AsyncKernelManager = app.state.kernel_manager
            await km.shutdown_kernel()
            app.state.kernel_manager, app.state.kernel_client = await _create_kernel()
        except Exception:
            logger.exception("Error while resetting kernel")
            return JSONResponse(status_code=500, content={"error": "Error while resetting kernel"})
        return JSONResponse(content={})


@app.post("/execute")
async def execute(request: ExecuteRequest) -> ExecuteResponse:
    try:
        kc: AsyncKernelClient = app.state.kernel_client
        code_message_id = kc.execute(
            request.code, silent=False, store_history=True, allow_stdin=False
        )
        return ExecuteResponse(
            code_message_id=code_message_id, error=None, kernel_status=await _get_kernel_status()
        )
    except Exception as e:
        logger.exception("Error while executing code")
        return ExecuteResponse(
            code_message_id="",
            error=ExecuteError.from_exception(e),
            kernel_status=await _get_kernel_status(),
        )


@app.post("/interrupt")
async def interrupt() -> JSONResponse:
    try:
        km: AsyncKernelManager = app.state.kernel_manager
        await km.interrupt_kernel()
    except Exception:
        logger.exception("Error while interrupting kernel")
        return JSONResponse(status_code=500, content={"error": "Error while interrupting kernel"})
    return JSONResponse(content="success")


                                                                                
@app.post("/caas_jupyter_tool/callback")
async def record_callback(request: CallbackRequest) -> JSONResponse:
\
\
\
\
\
       
    if request.name not in _ALLOWED_CALLBACKS:
        return JSONResponse(status_code=400, content={"error": "Invalid callback name"})

    async with app.state.callback_lock:
        app.state.recorded_callbacks.append(
            RecordedCallback(name=request.name, args=request.args, kwargs=request.kwargs)
        )
    return JSONResponse(content={})


@app.post("/caas_jupyter_tool/log_exception")
async def log_exception(body: LogExceptionRequest, request: Request) -> None:
    logger.error(
        f"caas_jupyter_tools exception logger: {body.message}, id={body.exception.id}, "
        f"orig_func_name={body.orig_func_name}, type={body.exception.type}, value={body.exception.value}",
        extra={
            "custom_message": body.message,
            "exception_id": body.exception.id,
            "exception_type": body.exception.type,
            "exception": body.exception.value,
            "traceback": body.exception.traceback,
            "orig_func_name": body.orig_func_name,
            "orig_func_args": body.orig_func_args,
            "orig_func_kwargs": body.orig_func_kwargs,
        },
    )


@app.post("/caas_jupyter_tool/log_matplotlib_img_fallback")
async def log_matplotlib_img_fallback(body: LogMatplotlibFallbackRequest, request: Request) -> None:
    logger.warning(
        f"caas_jupyter_tools matplotlib img fallback: reason={body.reason} metadata={body.metadata}",
        extra={"reason": body.reason, "metadata": body.metadata},
    )


async def _pull_message(timeout: float) -> IOPubMessage:
    kc: AsyncKernelClient = app.state.kernel_client
    raw = await kc.get_iopub_msg(timeout=timeout)
    message = parse_obj_as_io_pub_message(raw)
    return message


def _raise_if_oversized(result: IOPubMessage | None) -> None:
    if result is None:
        return
    size = len(result.model_dump_json())
    if size > _MAX_JUPYTER_MESSAGE_SIZE:
        raise UserMachineResponseTooLarge(
            f"User machine response too large: {size} bytes (max: {_MAX_JUPYTER_MESSAGE_SIZE} bytes)"
        )


@app.post("/pull_message")
async def pull_message(request: PullMessageRequest) -> PullMessageResponse:
    try:
        message = await _pull_message(request.timeout)
        _raise_if_oversized(message)
                                                        
        callbacks: list[RecordedCallback] = []
        async with app.state.callback_lock:
            while app.state.recorded_callbacks and len(callbacks) < _CALLBACK_PULL_LIMIT:
                callbacks.append(app.state.recorded_callbacks.popleft())
        return PullMessageResponse(
            message=message,
            error=None,
            kernel_status=await _get_kernel_status(),
            callbacks=callbacks,
        )
    except Exception as e:
        logger.exception(f"Error {e.__class__.__name__} while pulling message")
        return PullMessageResponse(
            message=None,
            error=ExecuteError.from_exception(e),
            kernel_status=await _get_kernel_status(),
            callbacks=[],
        )


if __name__ == "__main__":
    port = int(os.environ.get("API_PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
