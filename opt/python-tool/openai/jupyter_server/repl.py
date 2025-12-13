                                                               
 
                                                                           
                                                                         
                                                                       
                                                                                     
 
        
                                                                  

import argparse
import asyncio
import sys
from typing import Any, Mapping, Sequence

import httpx

from research_ace.v2.ace_types.jupyter_message import IOPubMessage
from research_ace.v2.ace_types.jupyter_server_types import (
    ExecuteRequest,
    ExecuteResponse,
    PullMessageRequest,
    PullMessageResponse,
)


def _render_mime_bundle(mime: Mapping[str, Any]) -> str:
                                                                      
    if "text/plain" in mime:
        return mime["text/plain"]
                                            
    return next(iter(mime.values())) if mime else ""


def _handle_message(message: IOPubMessage) -> bool:
\
\
       
    if message.msg_type == "stream":
                       
        sys.stdout.write(message.content.text)
        sys.stdout.flush()
    elif message.msg_type == "execute_result":
                         
        sys.stdout.write(_render_mime_bundle(message.content.data) + "\n")
        sys.stdout.flush()
    elif message.msg_type == "display_data":
        sys.stdout.write(_render_mime_bundle(message.content.data) + "\n")
        sys.stdout.flush()
    elif message.msg_type == "error":
        sys.stderr.write("\n".join(message.content.traceback) + "\n")
        sys.stderr.flush()
    elif message.msg_type == "status":
        if message.content.execution_state == "idle":
            return True
                                                  
    return False


async def _run_cell(client: httpx.AsyncClient, base_url: str, code: str) -> None:
                                                                             
    execute_resp_r = await client.post(
        f"{base_url}/execute", json=ExecuteRequest(code=code).model_dump()
    )
    execute_resp = ExecuteResponse.model_validate_json(execute_resp_r.text)
    execute_resp.raise_if_error()
    while True:
        pull_r = await client.post(
            f"{base_url}/pull_message",
            json=PullMessageRequest(timeout=1.0).model_dump(),
            timeout=2.0,
        )
        pull_resp = PullMessageResponse.model_validate_json(pull_r.text)
        pull_resp.raise_if_error()
        for cb in pull_resp.callbacks:
                                                         
            print(f"[callback {cb.name}] args={cb.args} kwargs={cb.kwargs}")
        if pull_resp.message:
            done = _handle_message(pull_resp.message)
            if done:
                break


async def repl(base_url: str) -> None:
                                                                                     
    async with httpx.AsyncClient() as client:
        while True:
            try:
                code = input(">>> ")
            except EOFError:
                break
            if not code.strip():
                continue
            try:
                await _run_cell(client, base_url, code)
            except Exception as e:
                print(f"Error during execution: {e}")


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="REPL for caas_jupyter_server")
    parser.add_argument(
        "--url",
        required=True,
        help="Base URL of running caas_jupyter_server (e.g. http://localhost:8080)",
    )
    args = parser.parse_args(argv)
    asyncio.run(repl(args.url))


if __name__ == "__main__":
    main()
