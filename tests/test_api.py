"""Інтеграційні перевірки HTML і JSON API."""


def test_home_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Сучасний".encode() in response.data


def test_about_page(client):
    response = client.get("/about")
    assert response.status_code == 200
    assert b"Open Linked Data" in response.data


def test_health_endpoint(client):
    payload = client.get("/api/health").json
    assert payload["status"] == "ok"
    assert payload["artists"] >= 200


def test_artists_api_filters(client):
    payload = client.get("/api/artists?search=Jinjer&type=group").json
    assert payload["count"] == 1
    assert payload["items"][0]["qid"] == "Q12071385"


def test_artist_endpoint(client):
    response = client.get("/api/artists/Q1008489")
    assert response.status_code == 200
    assert response.json["qid"] == "Q1008489"


def test_unverified_official_website_is_not_exposed(client):
    response = client.get("/api/artists/Q18762242")
    assert response.status_code == 200
    assert "website" not in response.json


def test_invalid_qid_is_rejected(client):
    assert client.get("/api/artists/not-a-qid").status_code == 400


def test_unknown_qid_is_404(client):
    assert client.get("/api/artists/Q999999999").status_code == 404


def test_turtle_export(client):
    response = client.get("/api/export/turtle")
    assert response.status_code == 200
    assert b"owl:sameAs" in response.data
    assert b"schema:MusicGroup" in response.data


def test_regular_404_page(client):
    response = client.get("/missing-page")
    assert response.status_code == 404
    assert b"404" in response.data

