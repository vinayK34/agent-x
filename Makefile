.PHONY: dev backend frontend test fmt down clean

dev:                    ## Run backend + frontend with hot reload
	@(cd backend && uvicorn app.main:app --reload --port 8000) & \
	 (cd frontend && npm install --silent && npm run dev)

backend:                ## Run just the backend
	cd backend && uvicorn app.main:app --reload --port 8000

frontend:               ## Run just the frontend
	cd frontend && npm install && npm run dev

test:                   ## Run backend tests
	cd backend && pytest -q

up:                     ## docker compose up
	docker compose up --build

down:
	docker compose down

clean:
	rm -rf backend/data frontend/.next frontend/node_modules
