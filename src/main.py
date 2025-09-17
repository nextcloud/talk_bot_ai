# SPDX-FileCopyrightText: 2023-2025 Nextcloud GmbH and Nextcloud contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Talk bot application that connects the Task Processing and Talk Bot APIs."""

import asyncio
from contextlib import asynccontextmanager
import json
import re
from typing import Annotated

from fastapi import BackgroundTasks, Depends, FastAPI, Query, Request, responses

from nc_py_api import NextcloudApp, talk_bot
from nc_py_api.talk_bot import TalkBotMessage
from nc_py_api.ex_app import (
    AppAPIAuthMiddleware,
    atalk_bot_msg,
    nc_app,
    run_app,
    set_handlers,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    set_handlers(app, enabled_handler)
    yield


APP = FastAPI(lifespan=lifespan)
APP.add_middleware(AppAPIAuthMiddleware)
BOT_URL = "talk_bot_ai"
AI_BOT = talk_bot.TalkBot("/" + BOT_URL, "Assistant Talk Bot", "Usage: `@assistant What sounds do cats make?`")


def ai_talk_bot_process_request(message: TalkBotMessage, nc: NextcloudApp):
    message_text = message.object_content["message"]
    prompt = re.search(r"@assistant\s+(.*)\s*", message_text, re.IGNORECASE | re.DOTALL)

    if prompt is None:
        return

    user = message.actor_id.split("/", maxsplit=1)[1]
    nc.set_user(user)

    params = {
        "input": {
            "input": prompt.group(1),
        },
        "type": "core:text2text",
        "appId": BOT_URL,
        "webhookUri": f"/message?reply_to={message.object_id}&token={message.conversation_token}",
        "webhookMethod": "AppAPI:" + BOT_URL + ":POST",
    }
    schedule = nc.ocs(method="POST", path="/ocs/v2.php/taskprocessing/schedule", json=params)

    if "message" in schedule:
        AI_BOT.send_message(f"ERROR: Unable to process request ({schedule["message"]})", message)

    return


@APP.post("/message")
def message_handler(
    request: Request,
    reply_to: Annotated[int, Query(description="ID of message to reply to")],
    token: Annotated[str, Query(description="Conversation token")]
):
    body = asyncio.run(request.body())
    task = json.loads(body)["task"]
    status = task["status"]
    # if status == "STATUS_CANCELLED", do nothing
    if status == "STATUS_FAILED":
        AI_BOT.send_message("ERROR: Failed to generate message, please try again later", reply_to, token=token)
    if status == "STATUS_SUCCESSFUL":
        AI_BOT.send_message(task["output"]["output"], reply_to, token=token)

    return responses.Response()


@APP.post("/" + BOT_URL)
async def ai_talk_bot(
    message: Annotated[TalkBotMessage, Depends(atalk_bot_msg)],
    nc: Annotated[NextcloudApp, Depends(nc_app)],
    background_tasks: BackgroundTasks,
):
    if message.object_name == "message":
        background_tasks.add_task(ai_talk_bot_process_request, message, nc)
    return responses.Response()


def enabled_handler(enabled: bool, nc: NextcloudApp):
    print(f"enabled={enabled}")
    try:
        AI_BOT.enabled_handler(enabled, nc)
    except Exception as e:
        return str(e)
    return ""


if __name__ == "__main__":
    run_app("main:APP", log_level="trace")
