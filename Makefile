.DEFAULT_GOAL := help

APP_ID := talk_bot_ai
APP_VERSION := 3.0.0
JSON_INFO := "{\"id\":\"$(APP_ID)\",\"name\":\"Assistant Talk Bot\",\"daemon_config_name\":\"manual_install\",\"version\":\"$(APP_VERSION)\",\"secret\":\"12345\",\"port\":10034,\"scopes\":[\"TALK\", \"TALK_BOT\"],\"system\":0}"

.PHONY: help
help:
	@echo "Welcome to the Nextcloud Assistant talk bot. Please use \`make <target>\` where <target> is one of"
	@echo " "
	@echo "  Next commands are only for dev environment with nextcloud-docker-dev!"
	@echo "  They should run from the host you are developing on(with activated venv) and not in the container with Nextcloud!"
	@echo "  "
	@echo "  build-push        build image and upload to ghcr.io"
	@echo "  "
	@echo "  run               install nextcloud_talk_bot for Nextcloud Latest"
	@echo "  run30             install nextcloud_talk_bot for Nextcloud 30"
	@echo "  "
	@echo "  For development of this app use PyCharm run configurations. Development is always set for last Nextcloud."
	@echo "  First run 'nextcloud_talk_bot' and then 'make register', after that you can use/debug/develop it and easy test."
	@echo "  "
	@echo "  register          perform registration of running 'nextcloud_talk_bot' into the 'manual_install' deploy daemon."
	@echo "  register30        perform registration of running 'nextcloud_talk_bot' into the 'manual_install' deploy daemon."

.PHONY: build-push
build-push:
	docker login ghcr.io
	docker buildx build --push --platform linux/arm64/v8,linux/amd64 --tag ghcr.io/cloud-py-api/$(APP_ID):$(APP_VERSION) --tag ghcr.io/cloud-py-api/$(APP_ID):latest .

.PHONY: run
run:
	docker exec master-nextcloud-1 sudo -u www-data php occ app_api:app:unregister $(APP_ID) --silent --force || true
	docker exec master-nextcloud-1 sudo -u www-data php occ app_api:app:register $(APP_ID) --force-scopes \
		--info-xml https://raw.githubusercontent.com/cloud-py-api/$(APP_ID)/main/appinfo/info.xml

.PHONY: run30
run30:
	docker exec master-stable30-1 sudo -u www-data php occ app_api:app:unregister $(APP_ID) --silent --force || true
	docker exec master-stable30-1 sudo -u www-data php occ app_api:app:register $(APP_ID) --force-scopes \
		--info-xml https://raw.githubusercontent.com/cloud-py-api/$(APP_ID)/main/appinfo/info.xml

.PHONY: register
register:
	docker exec master-nextcloud-1 sudo -u www-data php occ app_api:app:unregister $(APP_ID) --silent --force || true
	docker exec master-nextcloud-1 sudo -u www-data php occ app_api:app:register $(APP_ID) manual_install --json-info $(JSON_INFO) --force-scopes --wait-finish

.PHONY: register30
register30:
	docker exec master-stable30-1 sudo -u www-data php occ app_api:app:unregister $(APP_ID) --silent --force || true
	docker exec master-stable30-1 sudo -u www-data php occ app_api:app:register $(APP_ID) manual_install --json-info $(JSON_INFO) --force-scopes --wait-finish
