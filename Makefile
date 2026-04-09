.PHONY: run run-ghcr pull build up

IMAGE := ghcr.io/geraldf/openapi:latest

run-ghcr:
	docker pull $(IMAGE)
	docker run -d -p 7000:7000 --env-file .env --name openapi $(IMAGE)

run: build
	docker run -d -p 7000:7000 --env-file .env --name openapi docker-db-api

pull:
	docker pull $(IMAGE)

build:
	docker build -t docker-db-api .

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker logs -f openapi
