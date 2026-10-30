from fastapi.testclient import TestClient

from app.main import create_app


def test_health_is_ok_even_without_database(monkeypatch) -> None:
    from sqlalchemy import create_engine

    import app.api.health as health_module

    unreachable = create_engine(
        "postgresql+psycopg://nobody:nothing@127.0.0.1:1/none", connect_args={"connect_timeout": 1}
    )
    monkeypatch.setattr(health_module, "get_engine", lambda: unreachable)
    response = TestClient(create_app()).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "unavailable"}


def test_health_reports_database(engine) -> None:
    response = TestClient(create_app()).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "ok"}
