<!--
  - SPDX-FileCopyrightText: 2023-2025 Nextcloud GmbH and Nextcloud contributors
  - SPDX-License-Identifier: AGPL-3.0-or-later
-->

## Nextcloud Assistant Talk Bot

**A talk bot using [`AppAPI`],
the [OCS TaskProcessing API],
and [Talk Bot API].**

The bot is capable of answering questions in [Nextcloud Talk] chat conversations
using the large language model set by [Nextcloud Assistant].

## How to install:

1. Install [`AppAPI`]
	and set up a deploy daemon by following the [AppAPI instructions].
	_(Automatically created with AIO)_
2. Go to the `Apps` menu in Nextcloud,
	find this app (`Assistant Talk Bot`) in the `AI` or `Tools` category,
	and click `Deploy and Enable`.
3. In Nextcloud Talk,
	open a conversation and enable the bot in `Conversation settings`.
4. Invoke the bot by typing `@assistant` followed by your question
	(e.g., `@assistant I have a question for you.`).

<!-- Links -->

[`AppAPI`]: https://github.com/nextcloud/app_api
[OCS TaskProcessing API]: https://docs.nextcloud.com/server/latest/developer_manual/client_apis/OCS/ocs-taskprocessing-api.html
[Talk Bot API]: https://cloud-py-api.github.io/nc_py_api/reference/TalkBot.html
[Nextcloud Talk]: https://nextcloud.com/talk/
[Nextcloud Assistant]: https://nextcloud.com/assistant/
[AppAPI instructions]: https://docs.nextcloud.com/server/latest/admin_manual/exapps_management/AppAPIAndExternalApps.html
