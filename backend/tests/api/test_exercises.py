from app.models import Exercise
from app.models.enums import LoadType


def _seed(db_session) -> None:
    db_session.add_all(
        [
            Exercise(name="Squat", category="Legs", equipment="barbell"),
            Exercise(name="Pull Up", category="Back", load_type=LoadType.BODYWEIGHT_PLUS),
            Exercise(name="Old Machine Row", category="Back", archived=True),
        ]
    )
    db_session.flush()


def test_lists_active_exercises_sorted_by_name(client, db_session, auth_headers) -> None:
    _seed(db_session)
    response = client.get("/exercises", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    names = [e["name"] for e in body]
    assert names == sorted(names)
    assert "Squat" in names
    assert "Old Machine Row" not in names
    pull_up = next(e for e in body if e["name"] == "Pull Up")
    assert pull_up["load_type"] == "bodyweight_plus"
    assert pull_up["archived"] is False


def test_include_archived(client, db_session, auth_headers) -> None:
    _seed(db_session)
    response = client.get("/exercises", params={"include_archived": True}, headers=auth_headers)
    assert "Old Machine Row" in [e["name"] for e in response.json()]


def test_invalid_query_param_is_rejected(client, auth_headers) -> None:
    response = client.get("/exercises", params={"include_archived": "maybe"}, headers=auth_headers)
    assert response.status_code == 422


def test_requires_owner(client) -> None:
    assert client.get("/exercises").status_code == 401
    wrong = {"Authorization": "Bearer wrong"}
    assert client.get("/exercises", headers=wrong).status_code == 401
