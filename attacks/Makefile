build:
	docker-compose build

up:
	docker-compose up --build --abort-on-container-exit

upd:
	docker-compose up -d --build
	@echo "Containers started in background. Use 'make logs' to view output."

down:
	docker-compose down

clean:
	docker-compose down --rmi all -v

restart:
	docker-compose restart

rebuild:
	docker-compose down --rmi all -v
	docker-compose build --no-cache
	docker-compose up
