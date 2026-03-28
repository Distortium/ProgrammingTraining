# Programmer

Полноценная учебная платформа для детей 8–15 лет:
- 3 трека (`python`, `javascript`, `csharp`)
- практика с реальным запуском кода в Docker
- прогресс/XP/уровни/достижения
- родительский контроль
- сообщество (лидерборд, лента, чат)
- админ-конструктор курсов

## Стек И Зачем Он Нужен

| Слой | Технологии | Для чего |
|---|---|---|
| Frontend | `HTML + CSS + Vanilla JS` | UI приложения, уроки, практика, админка, родительский кабинет |
| Backend API | `FastAPI` | REST API, авторизация, бизнес-логика прогресса/курсов/сообщества |
| База данных | `PostgreSQL` | Постоянное хранение пользователей, курсов, прогресса, чата |
| ORM | `SQLAlchemy` | Модели и работа с БД |
| Выполнение кода | `Docker` + runner images (`python/node/dotnet`) | Изолированный и безопасный запуск пользовательского кода |
| Деплой локально | `Docker Compose` | Подъем `backend + postgres` одной командой |

## Что В Репозитории Используется Сейчас

- `frontend/` — рабочий веб-клиент
- `backend_api/` — рабочий API + Docker runners + БД схема
- `run_project.bat` — основной запуск всего проекта
- `run_frontend.bat` — только фронтенд (если backend уже поднят)

## Требования

1. Windows 10/11
2. Docker Desktop (запущен)
3. Python 3.11+ (`py -3` в PATH)

## Быстрый Старт (Рекомендуется)

Из корня проекта:

```bat
run_project.bat
```

Что делает скрипт:
1. Проверяет Docker CLI/daemon
2. Проверяет/собирает runner-образы
3. Поднимает `postgres + backend` через compose
4. Ждет `http://localhost:8000/health`
5. Стартует frontend на `0.0.0.0:5500`

После запуска:
- сайт: `http://localhost:5500`
- backend health: `http://localhost:8000/health`
- админ: `admin / admin12345`

## Полный Перезапуск Проекта

```bat
cd C:\ss\Programmer\backend_api
docker compose down -v --remove-orphans
cd C:\ss\Programmer
run_project.bat
```

Это удалит старую БД и поднимет всё заново.

## Доступ С Телефона В Той Же Сети

1. Запусти `run_project.bat`
2. Узнай LAN IP ПК (`ipconfig`, обычно `192.168.x.x`)
3. Открой с телефона:
   - `http://<LAN_IP_ПК>:5500`

Важно:
- ПК и телефон должны быть в одной локальной сети
- VPN лучше выключить на обоих устройствах
- в Windows Firewall должен быть открыт вход на порты `5500` и `8000`

## Ручной Запуск По Частям

### 1) Backend + PostgreSQL

```bat
cd C:\ss\Programmer\backend_api
docker compose up -d --build
```

### 2) Frontend

```bat
cd C:\ss\Programmer
run_frontend.bat
```

## Интеграция В Другой Проект

Ниже два типовых варианта.

### Вариант A: Использовать Только Backend API

1. Скопируй каталог `backend_api/` в свой проект
2. Подними его:

```bat
cd backend_api
docker compose up -d --build
```

3. Настрой на своем фронте:
- `baseURL = http://<host>:8000`
- `credentials: 'include'` для всех запросов (cookie-session)
- `Content-Type: application/json`

4. Добавь origin фронта в `FRONTEND_ORIGINS` (если нужен другой домен/порт)

### Вариант B: Встроить И Frontend, И Backend

1. Скопируй `frontend/` и `backend_api/`
2. Запускай одним `run_project.bat`
3. Если меняешь порт backend, обнови `frontend/js/app.js`:
- `DEFAULT_API_BASE`

## Основные API Эндпоинты

### Auth
- `POST /api/v1/auth/register/student`
- `POST /api/v1/auth/register/parent`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`

### Курсы и прогресс
- `GET /api/v1/courses`
- `GET /api/v1/courses?track=python|javascript|csharp`
- `POST /api/v1/progress/lessons/{lesson_id}/complete`
- `POST /api/v1/progress/quizzes/{lesson_id}/submit`
- `GET /api/v1/progress/me`

### Практика
- `POST /api/v1/practice/run`
- legacy: `POST /run`

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

### Админ-конструктор
- `GET/POST/PUT/DELETE /api/v1/admin/courses`
- `POST/PUT/DELETE /api/v1/admin/modules`
- `POST/PUT/DELETE /api/v1/admin/lessons`
- `POST/PUT/DELETE /api/v1/admin/questions`
- `POST /api/v1/admin/practice-checks`

## Переменные Окружения (Backend)

Файл-шаблон: `backend_api/.env.example`

Критичные:
- `DATABASE_URL`
- `FRONTEND_ORIGINS`
- `SESSION_COOKIE_NAME`
- `SESSION_TTL_HOURS`
- `SESSION_SECURE_COOKIE`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `PYTHON_RUNNER_IMAGE`
- `JAVASCRIPT_RUNNER_IMAGE`
- `CSHARP_RUNNER_IMAGE`

## Тесты

```bat
cd C:\ss\Programmer\backend_api
py -3 -m pytest -q
```

## Диагностика

Проверка контейнеров:

```bat
cd C:\ss\Programmer\backend_api
docker compose ps
docker compose logs --tail=100 backend
```

Проверка API:

```bat
curl http://localhost:8000/health
```

Если фронт открылся, но API не работает:
1. Проверь `docker compose ps`
2. Проверь CORS (`FRONTEND_ORIGINS`)
3. Проверь, что запросы идут с `credentials: include`
