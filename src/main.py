"""Example of an application that uses Python Transformers library with Talk Bot APIs."""

import os

# This line should be on top before any import of the "Transformers" library.
os.environ["TRANSFORMERS_CACHE"] = os.environ["APP_PERSISTENT_STORAGE"]  # noqa

import asyncio
import dataclasses
import re
from threading import Thread
from typing import Annotated
from base64 import b64encode, b64decode
from random import choice
from string import ascii_lowercase, ascii_uppercase, digits
import hmac
import typing
import hashlib

import httpx
import json
import requests
from fastapi import BackgroundTasks, Depends, FastAPI, responses, Request, HTTPException, status
from transformers import pipeline
import uvicorn

APP = FastAPI()
MODEL_NAME = "MBZUAI/LaMini-Flan-T5-248M"
MODEL_INIT_THREAD = None
BOT_URL = "/ai_talk_bot_example"


@dataclasses.dataclass
class TalkBotMessage:
    def __init__(self, raw_data: dict):
        self._raw_data = raw_data

    @property
    def actor_id(self) -> str:
        return self._raw_data["actor"]["id"]

    @property
    def actor_display_name(self) -> str:
        return self._raw_data["actor"]["name"]

    @property
    def object_id(self) -> int:
        return self._raw_data["object"]["id"]

    @property
    def object_name(self) -> str:
        return self._raw_data["object"]["name"]

    @property
    def object_content(self) -> dict:
        return json.loads(self._raw_data["object"]["content"])

    @property
    def object_media_type(self) -> str:
        return self._raw_data["object"]["mediaType"]

    @property
    def conversation_token(self) -> str:
        return self._raw_data["target"]["id"]

    @property
    def conversation_name(self) -> str:
        return self._raw_data["target"]["name"]


def get_nc_url() -> str:
    return os.environ["NEXTCLOUD_URL"].removesuffix("/index.php").removesuffix("/")


def sign_request(headers: dict, user="") -> None:
    headers["AUTHORIZATION-APP-API"] = b64encode(f"{user}:{os.environ['APP_SECRET']}".encode("UTF=8"))
    headers["EX-APP-ID"] = os.environ["APP_ID"]
    headers["EX-APP-VERSION"] = os.environ["APP_VERSION"]
    headers["OCS-APIRequest"] = "true"


def sign_check(request: Request) -> str:
    headers = {
        "AA-VERSION": request.headers["AA-VERSION"],
        "EX-APP-ID": request.headers["EX-APP-ID"],
        "EX-APP-VERSION": request.headers["EX-APP-VERSION"],
        "AUTHORIZATION-APP-API": request.headers.get("AUTHORIZATION-APP-API", ""),
    }
    # AA-VERSION contains AppAPI version, for now it can be only one version, so no handling of it.
    if headers["EX-APP-ID"] != os.environ["APP_ID"]:
        raise ValueError(f"Invalid EX-APP-ID:{headers['EX-APP-ID']} != {os.environ['APP_ID']}")

    if headers["EX-APP-VERSION"] != os.environ["APP_VERSION"]:
        raise ValueError(f"Invalid EX-APP-VERSION:{headers['EX-APP-VERSION']} <=> {os.environ['APP_VERSION']}")

    auth_aa = b64decode(headers.get("AUTHORIZATION-APP-API", "")).decode("UTF-8")
    username, app_secret = auth_aa.split(":", maxsplit=1)
    if app_secret != os.environ["APP_SECRET"]:
        raise ValueError(f"Invalid APP_SECRET:{app_secret} != {os.environ['APP_SECRET']}")
    return username


def ocs_call(
    method: str,
    path: str,
    params: typing.Optional[dict] = None,
    json_data: typing.Optional[typing.Union[dict, list]] = None,
    **kwargs,
):
    method = method.upper()
    if params is None:
        params = {}
    params.update({"format": "json"})
    headers = kwargs.pop("headers", {})
    data_bytes = None
    if json_data is not None:
        headers.update({"Content-Type": "application/json"})
        data_bytes = json.dumps(json_data).encode("utf-8")
    sign_request(headers, kwargs.get("user", ""))
    return httpx.request(
        method,
        url=get_nc_url() + path,
        params=params,
        content=data_bytes,
        headers=headers,
    )


def random_string(size: int) -> str:
    return "".join(choice(ascii_lowercase + ascii_uppercase + digits) for _ in range(size))


def get_bot_secret(callback_url: str) -> bytes:
    sha_1 = hashlib.sha1(usedforsecurity=False)
    string_to_hash = os.environ["APP_ID"] + "_" + callback_url
    sha_1.update(string_to_hash.encode("UTF-8"))
    secret_key = sha_1.hexdigest()
    if secret_key in os.environ:
        return os.environ[secret_key].encode("UTF-8")
    data = {"configKeys": [secret_key]}
    results = ocs_call(
        method="POST", path=f"/ocs/v1.php/apps/app_api/api/v1/ex-app/config/get-values", json_data=data
    )
    r = json.loads(results.text)["ocs"]["data"]
    secret_value = r[0]["configvalue"]
    os.environ[secret_key] = secret_value
    return secret_value.encode("UTF-8")


def _sign_send_request(method: str, url_suffix: str, data: dict, data_to_sign: str) -> httpx.Response:
    secret = get_bot_secret(BOT_URL)
    talk_bot_random = random_string(32)
    hmac_sign = hmac.new(secret, talk_bot_random.encode("UTF-8"), digestmod=hashlib.sha256)
    hmac_sign.update(data_to_sign.encode("UTF-8"))
    headers = {
        "X-Nextcloud-Talk-Bot-Random": talk_bot_random,
        "X-Nextcloud-Talk-Bot-Signature": hmac_sign.hexdigest(),
        "OCS-APIRequest": "true",
    }
    return httpx.request(
        method,
        url=get_nc_url() + "/ocs/v2.php/apps/spreed/api/v1/bot" + url_suffix,
        json=data,
        headers=headers,
    )


def send_message(
    message: str, reply_to_message: typing.Union[int, TalkBotMessage], silent: bool = False, token: str = ""
) -> tuple[httpx.Response, str]:
    if not token and not isinstance(reply_to_message, TalkBotMessage):
        raise ValueError("Either specify 'token' value or provide 'TalkBotMessage'.")
    token = reply_to_message.conversation_token if isinstance(reply_to_message, TalkBotMessage) else token
    reference_id = hashlib.sha256(random_string(32).encode("UTF-8")).hexdigest()
    params = {
        "message": message,
        "replyTo": reply_to_message.object_id if isinstance(reply_to_message, TalkBotMessage) else reply_to_message,
        "referenceId": reference_id,
        "silent": silent,
    }
    return _sign_send_request("POST", f"/{token}/message", params, message), reference_id


def talk_bot_app(request: Request) -> TalkBotMessage:
    body = asyncio.run(request.body())
    secret = get_bot_secret(request.url.components.path)
    if not secret:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    hmac_sign = hmac.new(
        secret, request.headers.get("X-NEXTCLOUD-TALK-RANDOM", "").encode("UTF-8"), digestmod=hashlib.sha256
    )
    hmac_sign.update(body)
    if request.headers["X-NEXTCLOUD-TALK-SIGNATURE"] != hmac_sign.hexdigest():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return TalkBotMessage(json.loads(body))


def ai_talk_bot_process_request(message: TalkBotMessage):
    r = re.search(r"@assistant\s(.*)", message.object_content["message"], re.IGNORECASE)
    if r is None:
        return
    model = pipeline("text2text-generation", model=MODEL_NAME)
    response_text = model(r.group(1), max_length=64, do_sample=True)[0]["generated_text"]
    send_message(response_text, message)


@APP.post(BOT_URL)
async def ai_talk_bot(
    message: Annotated[TalkBotMessage, Depends(talk_bot_app)],
    background_tasks: BackgroundTasks,
):
    if message.object_name == "message":
        background_tasks.add_task(ai_talk_bot_process_request, message)
    return requests.Response()


@APP.put("/enabled")
def enabled_handler(enabled: bool, request: Request):
    try:
        sign_check(request)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    print(f"enabled={enabled}")
    try:
        if enabled:
            params = {
                "name": "AI talk bot example",
                "route": BOT_URL,
                "description": "Usage: `@assistant What sounds do cats make?`",
            }
            result = ocs_call(method="POST", path="/ocs/v1.php/apps/app_api/api/v1/talk_bot", json_data=params)
            result_dict = json.loads(result.text)["ocs"]["data"]
            os.environ[result_dict["id"]] = result_dict["secret"]
        else:
            ocs_call(
                method="DELETE", path="/ocs/v1.php/apps/app_api/api/v1/talk_bot", json_data={"route": BOT_URL}
            )
        r = ""
    except Exception as e:
        r = str(e)
    return responses.JSONResponse(content={"error": r}, status_code=200)


def download_models():
    pipeline("text2text-generation", model=MODEL_NAME)


@APP.get("/heartbeat")
def heartbeat_handler():
    global MODEL_INIT_THREAD
    print("heartbeat_handler: called")
    if MODEL_INIT_THREAD is None:
        MODEL_INIT_THREAD = Thread(target=download_models)
        MODEL_INIT_THREAD.start()
        print("heartbeat_handler: started initialization thread")
    r = "init" if MODEL_INIT_THREAD.is_alive() else "ok"
    print(f"heartbeat_handler: result={r}")
    return responses.JSONResponse(content={"status": r}, status_code=200)


if __name__ == "__main__":
    uvicorn.run(
        "main:APP", host=os.environ.get("APP_HOST", "127.0.0.1"), port=int(os.environ["APP_PORT"]), log_level="trace"
    )
