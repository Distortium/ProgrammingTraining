# Programmer

Полноценная учебная веб-платформа для детей 8-15 лет.

## Что есть в проекте

- 2 трека: `python`, `javascript`
- практика с реальным запуском кода в Docker runner'ах
- прогресс: XP, уровни, достижения
- родительский контроль
- сообщество: лидерборд, лента, чат
- admin-конструктор курсов
- cookie-сессии (без JWT)

## Текущий стек

### Frontend

- `HTML5`
- `CSS3`
- `Vanilla JavaScript`
- локальный сервер: `py -3 -m http.server`

### Backend

- `Python 3.11`
- `FastAPI`
- `Uvicorn`
- `SQLAlchemy`
- `PostgreSQL`
- `Docker` + `Docker Compose`

### Runner images

- `local-code-runner-python:latest` (`python:3.11-slim`)
- `local-code-runner-javascript:latest` (`node:20-slim`)

## Архитектура

- `frontend/` - клиент
- `backend_api/` - API, БД-модели, бизнес-логика, runner orchestration
- `run_project.bat` - единый запуск проекта
- `run_frontend.bat` - запуск только frontend

## Требования

1. Windows 10/11
2. Docker Desktop (запущен)
3. Python 3.11+ (`py -3` в PATH)

## Быстрый запуск

Из корня проекта:

```bat
run_project.bat
```

Скрипт делает:

1. проверяет Docker CLI/daemon
2. проверяет/собирает runner-образы (python/javascript)
3. поднимает `postgres + backend` через compose
4. ждёт health-check API
5. запускает frontend на `0.0.0.0:5500`

После старта:

- сайт: `http://localhost:5500`
- API health: `http://localhost:8000/health`
- админ: `admin / admin12345`

## Запуск по частям

### Backend + PostgreSQL

```bat
cd C:\ss\Programmer\backend_api
docker compose up -d --build
```

### Только frontend

```bat
cd C:\ss\Programmer
run_frontend.bat
```

## Полная остановка

```bat
cd C:\ss\Programmer\backend_api
docker compose down --remove-orphans
```

## Полный перезапуск с очисткой БД

```bat
cd C:\ss\Programmer\backend_api
docker compose down -v --remove-orphans
cd C:\ss\Programmer
run_project.bat
```

## Доступ с телефона в той же сети

1. Запусти `run_project.bat`
2. Узнай IP ПК (`ipconfig`)
3. Открой с телефона `http://<IP_ПК>:5500`

Важно:

- ПК и телефон должны быть в одной локальной сети
- лучше выключить VPN на обоих устройствах
- открыть порты `5500` и `8000` во входящих правилах Windows Firewall

## Переменные окружения backend

Шаблон: `backend_api/.env.example`

Ключевые переменные:

- `DATABASE_URL`
- `FRONTEND_ORIGINS`
- `SESSION_COOKIE_NAME`
- `SESSION_TTL_HOURS`
- `SESSION_SECURE_COOKIE`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `PYTHON_RUNNER_IMAGE`
- `JAVASCRIPT_RUNNER_IMAGE`

## Основные API

### Auth

- `POST /api/v1/auth/register/student`
- `POST /api/v1/auth/register/parent`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`

### Курсы и прогресс

- `GET /api/v1/courses`
- `GET /api/v1/courses?track=python|javascript`
- `POST /api/v1/progress/lessons/{lesson_id}/complete`
- `POST /api/v1/progress/quizzes/{lesson_id}/submit`
- `GET /api/v1/progress/me`

### Практика

- `POST /api/v1/practice/run`
- `POST /run` (legacy)

### Родительский контроль

- `POST /api/v1/parent/requests`
- `GET /api/v1/parent/requests/incoming`
- `POST /api/v1/parent/requests/{id}/accept`
- `POST /api/v1/parent/requests/{id}/reject`
- `GET /api/v1/parent/children`
- `GET /api/v1/parent/children/{child_id}/progress`

### Сообщество

- `GET /api/v1/community/leaderboard`
- `GET/POST /api/v1/community/feed`
- `GET/POST /api/v1/community/chat`

### Admin builder

- `GET/POST/PUT/DELETE /api/v1/admin/courses`
- `POST/PUT/DELETE /api/v1/admin/modules`
- `POST/PUT/DELETE /api/v1/admin/lessons`
- `POST/PUT/DELETE /api/v1/admin/questions`
- `POST /api/v1/admin/practice-checks`

## Тесты

```bat
cd C:\ss\Programmer\backend_api
py -3 -m pytest -q
```

## Диагностика

### Проверка контейнеров

```bat
cd C:\ss\Programmer\backend_api
docker compose ps
docker compose logs --tail=100 backend
```

### Если backend долго собирается на шаге apt-get

В текущей версии это уже исправлено: backend-образ не ставит `docker.io` через apt.
Он копирует `docker` CLI из `docker:27-cli` (multi-stage build).

Если видишь в логах старый шаг `apt-get install -y docker.io` или сборку лишнего runner-образа, значит запущена старая версия проекта. Обнови репозиторий и запусти снова.
