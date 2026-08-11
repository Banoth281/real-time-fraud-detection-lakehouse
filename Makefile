.PHONY: up down logs test monitoring clean
up:
	docker compose up --build -d
down:
	docker compose down
logs:
	docker compose logs -f producer processor api
test:
	pytest -q
monitoring:
	docker compose --profile monitoring up -d
clean:
	docker compose down -v

