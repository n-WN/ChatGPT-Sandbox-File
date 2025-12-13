from typing import Any, Literal

import pydantic

                                                                
                                                                                                      


class IOPubParentHeader(pydantic.BaseModel):
    msg_id: str
    version: str


class IOPubStatusContent(pydantic.BaseModel):
    execution_state: Literal["busy", "idle", "starting"]


class IOPubStatus(pydantic.BaseModel):
    msg_type: Literal["status"]
    parent_header: IOPubParentHeader
    content: IOPubStatusContent


class IOPubStreamContent(pydantic.BaseModel):
    name: Literal["stdout", "stderr"]
    text: str


class IOPubStream(pydantic.BaseModel):
    msg_type: Literal["stream"]
    parent_header: IOPubParentHeader
    content: IOPubStreamContent


IOPubMimeBundle = dict[str, str]


class IOPubExecuteResultContent(pydantic.BaseModel):
    data: IOPubMimeBundle


class IOPubExecuteResult(pydantic.BaseModel):
    parent_header: IOPubParentHeader
    msg_type: Literal["execute_result"]
    content: IOPubExecuteResultContent


class IOPubDisplayDataContent(pydantic.BaseModel):
    data: IOPubMimeBundle


class IOPubDisplayData(pydantic.BaseModel):
    msg_type: Literal["display_data"]
    parent_header: IOPubParentHeader
    content: IOPubDisplayDataContent


class IOPubErrorContent(pydantic.BaseModel):
    traceback: list[str]
    ename: str
    evalue: str


class IOPubError(pydantic.BaseModel):
    msg_type: Literal["error"]
    parent_header: IOPubParentHeader
    content: IOPubErrorContent


class IOPubExecuteInput(pydantic.BaseModel):
    msg_type: Literal["execute_input"]
    parent_header: IOPubParentHeader


IOPubMessage = (
    IOPubStatus
    | IOPubStream
    | IOPubExecuteResult
    | IOPubDisplayData
    | IOPubError
    | IOPubExecuteInput
)


def parse_obj_as_io_pub_message(obj: Any) -> IOPubMessage:
    return pydantic.TypeAdapter(IOPubMessage).validate_python(obj)


class JupyterStartMessage(pydantic.BaseModel):
    msg_type: Literal["@start_message"] = "@start_message"
    run_id: str
    code: str
    code_message_id: str
    start_time: float


class JupyterTimeoutMessage(pydantic.BaseModel):
    msg_type: Literal["@timeout"] = "@timeout"
    timeout: float


                                                      
class JupyterCallbackMessage(pydantic.BaseModel):
    msg_type: Literal["@recorded_callback"] = "@recorded_callback"
    name: str
    args: list[Any] = []
    kwargs: dict[str, Any] = {}


JupyterMessage = JupyterStartMessage | JupyterTimeoutMessage | IOPubMessage | JupyterCallbackMessage
