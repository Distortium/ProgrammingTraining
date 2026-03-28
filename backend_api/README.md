# Programmer Backend API

Основная документация: [../README.md](../README.md)

Этот файл содержит только backend-специфику.

## Быстрый запуск

```bat
cd C:\ss\Programmer\backend_api
docker compose up -d --build
```

Проверка:

```bat
curl http://localhost:8000/health
```

## Что поднимается

- `programmer_postgres` (`postgres:16`)
- `programmer_backend` (FastAPI)

## Runner images

- `local-code-runner-python:latest`
- `local-code-runner-javascript:latest`

`run_project.bat` собирает их автоматически.

Ручная сборка:

```bat
docker build -t local-code-runner-python:latest runners/python
docker build -t local-code-runner-javascript:latest runners/javascript
```

## Тесты

```bat
cd C:\ss\Programmer\backend_api
py -3 -m pytest -q
```
