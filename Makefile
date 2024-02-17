.DEFAULT_GOAL := help

.PHONY: help
help:
	@echo "Welcome to TalkBotAI example. Please use \`make <target>\` where <target> is one of"
	@echo " "
	@echo "  Next commands are only for dev environment with nextcloud-docker-dev!"
	@echo "  They should run from the host you are developing on(with activated venv) and not in the container with Nextcloud!"
	@echo "  "
	@echo "  build-push        build image and upload to ghcr.io"
	@echo "  "
	@echo "  run28             install TalkBotAI for Nextcloud 28"
	@echo "  run27             install TalkBotAI for Nextcloud 27"
	@echo "  "
	@echo "  For development of this example use PyCharm run configurations. Development is always set for last Nextcloud."
	@echo "  First run 'TalkBotAI' and then 'make register', after that you can use/debug/develop it and easy test."
	@echo "  "
	@echo "  register28        perform registration of running 'TalkBotAI' into the 'manual_install' deploy daemon."
	@echo "  register27        perform registration of running 'TalkBotAI' into the 'manual_install' deploy daemon."

.PHONY: build-push
build-push:
	docker login ghcr.io
	docker buildx build --push --platform linux/arm64/v8,linux/amd64 --tag ghcr.io/cloud-py-api/talk_bot_ai_example:2.1.0 --tag ghcr.io/cloud-py-api/talk_bot_ai_example:latest .

.PHONY: run28
run28:
	docker exec master-nextcloud-1 sudo -u www-data php occ app_api:app:unregister talk_bot_ai_example --silent --force || true
	docker exec master-nextcloud-1 sudo -u www-data php occ app_api:app:register talk_bot_ai_example --force-scopes \
		--info-xml https://raw.githubusercontent.com/cloud-py-api/talk_bot_ai_example/main/appinfo/info.xml

.PHONY: run27
run27:
	docker exec master-stable27-1 sudo -u www-data php occ app_api:app:unregister talk_bot_ai_example --silent --force || true
	docker exec master-stable27-1 sudo -u www-data php occ app_api:app:register talk_bot_ai_example --force-scopes \
		--info-xml https://raw.githubusercontent.com/cloud-py-api/talk_bot_ai_example/main/appinfo/info.xml

.PHONY: register28
register28:
	docker exec master-nextcloud-1 sudo -u www-data php occ app_api:app:unregister talk_bot_ai_example --silent --force || true
	docker exec master-nextcloud-1 sudo -u www-data php occ app_api:app:register talk_bot_ai_example manual_install --json-info \
  "{\"id\":\"talk_bot_ai_example\",\"name\":\"TalkBotAI Example\",\"daemon_config_name\":\"manual_install\",\"version\":\"1.0.0\",\"secret\":\"12345\",\"port\":10034,\"scopes\":[\"TALK\", \"TALK_BOT\"],\"system\":0}" \
  --force-scopes --wait-finish

.PHONY: register27
register27:
	docker exec master-stable27-1 sudo -u www-data php occ app_api:app:unregister talk_bot_ai_example --silent --force || true
	docker exec master-stable27-1 sudo -u www-data php occ app_api:app:register talk_bot_ai_example manual_install --json-info \
  "{\"id\":\"talk_bot_ai_example\",\"name\":\"TalkBotAI Example\",\"daemon_config_name\":\"manual_install\",\"version\":\"1.0.0\",\"secret\":\"12345\",\"port\":10034,\"scopes\":[\"TALK\", \"TALK_BOT\"],\"system\":0}" \
  --force-scopes --wait-finish
