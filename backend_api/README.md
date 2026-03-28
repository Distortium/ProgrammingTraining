# Programmer Backend API

Основная документация проекта: [../README.md](../README.md)

Этот файл содержит только backend-специфику.

## Быстрый Запуск Backend

```bat
cd C:\ss\Programmer\backend_api
docker compose up -d --build
```

Проверка:

```bat
curl http://localhost:8000/health
```

## Что Поднимается

- `programmer_postgres` (`postgres:16`)
- `programmer_backend` (FastAPI)

## Runner Images (обязательны)

- `local-code-runner-python:latest`
- `local-code-runner-javascript:latest`
- `local-code-runner-csharp:latest`

`run_project.bat` собирает их автоматически.  
Если нужен ручной режим:

```bat
docker build -t local-code-runner-python:latest runners/python
docker build -t local-code-runner-javascript:latest runners/javascript
docker build -t local-code-runner-csharp:latest runners/csharp
```

## Тесты Backend

```bat
cd C:\ss\Programmer\backend_api
py -3 -m pytest -q
```
