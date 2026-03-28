import os
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test_programmer.db"
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "admin12345"
os.environ["FRONTEND_ORIGINS"] = "http://127.0.0.1:5500"

from fastapi.testclient import TestClient

from server.db import SessionLocal, engine
from server.db_models import Base, User, UserRole
from server.main import app

DB_FILE = Path("test_programmer.db")


def reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    if DB_FILE.exists():
        # SQLite DB is open via engine; drop/create is enough.
        pass


def register_and_login(client: TestClient, username: str, password: str, role: str = "student"):
    if role == "student":
        r = client.post(
            "/api/v1/auth/register/student",
            json={"username": username, "password": password, "age": 12},
        )
    else:
        r = client.post(
            "/api/v1/auth/register/parent",
            json={"username": username, "password": password},
        )
    assert r.status_code == 200, r.text

    r = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text


def test_auth_and_courses():
    reset_db()
    with TestClient(app) as client:
        register_and_login(client, "alice", "pass1234", "student")

        me = client.get("/api/v1/auth/me")
        assert me.status_code == 200
        assert me.json()["user"]["username"] == "alice"

        courses = client.get("/api/v1/courses")
        assert courses.status_code == 200
        items = courses.json()["items"]
        tracks = {c["track"] for c in items}
        assert {"python", "javascript"}.issubset(tracks)


def test_progress_and_quiz_submission():
    reset_db()
    with TestClient(app) as client:
        register_and_login(client, "bob", "pass1234", "student")

        courses = client.get("/api/v1/courses?track=python").json()["items"]
        course = courses[0]
        quiz_lesson = None
        for mod in course["modules"]:
            for lesson in mod["lessons"]:
                if lesson["lesson_type"] == "quiz":
                    quiz_lesson = lesson
                    break
            if quiz_lesson:
                break
        assert quiz_lesson is not None

        answers = {}
        for q in quiz_lesson["questions"]:
            answers[q["id"]] = q["options"][0]["id"]

        submit = client.post(
            f"/api/v1/progress/quizzes/{quiz_lesson['id']}/submit",
            json={"answers": answers},
        )
        assert submit.status_code == 200, submit.text
        body = submit.json()
        assert "score" in body and "completion" in body

        me = client.get("/api/v1/progress/me")
        assert me.status_code == 200
        assert me.json()["user"]["lessons_completed"] >= 1


def test_parent_flow_and_community():
    reset_db()
    with TestClient(app) as parent_client:
        register_and_login(parent_client, "mom", "pass1234", "parent")

        with TestClient(app) as student_client:
            register_and_login(student_client, "kid", "pass1234", "student")

            req = parent_client.post("/api/v1/parent/requests", json={"child_username": "kid"})
            assert req.status_code == 200
            req_id = req.json()["request_id"]

            incoming = student_client.get("/api/v1/parent/requests/incoming")
            assert incoming.status_code == 200
            assert len(incoming.json()["items"]) == 1

            accept = student_client.post(f"/api/v1/parent/requests/{req_id}/accept")
            assert accept.status_code == 200

            children = parent_client.get("/api/v1/parent/children")
            assert children.status_code == 200
            assert len(children.json()["items"]) == 1

            post = student_client.post("/api/v1/community/feed", json={"content": "Я прошел урок!"})
            assert post.status_code == 200

            feed = parent_client.get("/api/v1/community/feed")
            assert feed.status_code == 200
            assert len(feed.json()["items"]) >= 1

            msg = student_client.post("/api/v1/community/chat", json={"content": "Всем привет"})
            assert msg.status_code == 200

            chat = parent_client.get("/api/v1/community/chat")
            assert chat.status_code == 200
            assert len(chat.json()["items"]) >= 1


def test_admin_crud_course_builder():
    reset_db()
    with TestClient(app) as client:
        login = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin12345"})
        assert login.status_code == 200

        new_course = client.post(
            "/api/v1/admin/courses",
            json={
                "track": "python",
                "title": "Admin Course",
                "description": "Custom",
                "is_published": True,
            },
        )
        assert new_course.status_code == 200
        course_id = new_course.json()["id"]

        module = client.post(
            "/api/v1/admin/modules",
            json={
                "course_id": course_id,
                "title": "Admin Module",
                "description": "Module desc",
                "difficulty": "easy",
                "color": "#123456",
                "emoji": "📘",
                "unlock_xp": 0,
                "xp_reward": 20,
                "order_index": 1,
            },
        )
        assert module.status_code == 200

        courses = client.get("/api/v1/admin/courses")
        assert courses.status_code == 200
        assert any(c["id"] == course_id for c in courses.json()["items"])

