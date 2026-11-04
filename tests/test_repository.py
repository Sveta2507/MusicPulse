"""Перевірки запитів до локального сховища."""


def test_snapshot_is_loaded(service):
    assert service.repository.count() >= 200


def test_search_is_case_insensitive(service):
    items = service.list_artists(search="JINJER")
    assert [item["qid"] for item in items] == ["Q12071385"]


def test_type_filter_returns_people(service):
    items = service.list_artists(artist_type="person")
    assert items
    assert all(item["artist_type"] == "person" for item in items)


def test_genre_filter_uses_many_to_many_relation(service):
    genre = service.get_artist("Q12071385")["genres"][0]["name"]
    items = service.list_artists(genre=genre)
    assert "Q12071385" in {item["qid"] for item in items}


def test_sort_by_year_descending(service):
    years = [item["start_year"] for item in service.list_artists(sort="year_desc") if item["start_year"]]
    assert years == sorted(years, reverse=True)


def test_unknown_artist_returns_none(service):
    assert service.get_artist("Q999999999") is None


def test_stats_are_consistent(service):
    stats = service.stats()
    assert stats["artists"] == stats["groups"] + stats["persons"]
    assert stats["genres"] >= 10
    assert stats["metadata"]["license"] == "CC0 1.0"

