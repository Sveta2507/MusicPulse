"""Репозиторій, що ізолює SQL від решти застосунку."""

from __future__ import annotations

from collections import Counter
from typing import Any

from .database import Database


class ArtistRepository:
    """Зберігає, шукає та агрегує музичні сутності."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def replace_all(self, payload: dict[str, Any]) -> None:
        """Атомарно замінює набір даних новим знімком Wikidata."""
        with self.database.connect() as connection:
            connection.execute("DELETE FROM artist_genres")
            connection.execute("DELETE FROM genres")
            connection.execute("DELETE FROM artists")
            for artist in payload["artists"]:
                connection.execute(
                    """
                    INSERT INTO artists (
                        qid, name_uk, name_en, description, artist_type, start_year,
                        website, image_url, image_local, wikidata_url, spotify_url,
                        youtube_url, retrieved_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        artist["qid"], artist["name_uk"], artist["name_en"],
                        artist["description"], artist["artist_type"], artist.get("start_year"),
                        artist.get("website"), artist.get("image_url"), artist.get("image_local"),
                        artist["wikidata_url"], artist.get("spotify_url"), artist.get("youtube_url"),
                        artist["retrieved_at"],
                    ),
                )
                for genre in artist.get("genres", []):
                    connection.execute(
                        "INSERT OR IGNORE INTO genres (id, name) VALUES (?, ?)",
                        (genre["id"], genre["name"]),
                    )
                    connection.execute(
                        "INSERT INTO artist_genres (artist_qid, genre_id) VALUES (?, ?)",
                        (artist["qid"], genre["id"]),
                    )
            for key in ("source", "license", "retrieved_at"):
                connection.execute(
                    "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
                    (key, str(payload.get(key, ""))),
                )

    def count(self) -> int:
        """Повертає кількість виконавців у сховищі."""
        with self.database.connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM artists").fetchone()[0])

    def _genres(self, connection: Any, qid: str) -> list[dict[str, str]]:
        rows = connection.execute(
            """
            SELECT g.id, g.name FROM genres g
            JOIN artist_genres ag ON ag.genre_id = g.id
            WHERE ag.artist_qid = ? ORDER BY g.name COLLATE NOCASE
            """,
            (qid,),
        ).fetchall()
        return [dict(row) for row in rows]

    def _to_dict(self, connection: Any, row: Any) -> dict[str, Any]:
        artist = dict(row)
        # P856 у Wikidata може містити домен, який згодом прострочили й перекупили.
        # Значення зберігається як джерельне, але не передається користувачеві без перевірки.
        artist.pop("website", None)
        artist["genres"] = self._genres(connection, artist["qid"])
        return artist

    def list_artists(
        self,
        search: str = "",
        genre: str = "",
        artist_type: str = "",
        sort: str = "name",
    ) -> list[dict[str, Any]]:
        """Повертає відфільтрований і відсортований список виконавців."""
        where: list[str] = []
        params: list[Any] = []
        if search:
            where.append("(LOWER(a.name_uk) LIKE ? OR LOWER(a.name_en) LIKE ? OR LOWER(a.description) LIKE ?)")
            pattern = f"%{search.lower()}%"
            params.extend([pattern, pattern, pattern])
        if artist_type in {"group", "person"}:
            where.append("a.artist_type = ?")
            params.append(artist_type)
        if genre:
            where.append(
                "EXISTS (SELECT 1 FROM artist_genres x JOIN genres g ON g.id = x.genre_id "
                "WHERE x.artist_qid = a.qid AND g.name = ?)"
            )
            params.append(genre)
        order = {
            "name": "a.name_uk COLLATE NOCASE ASC",
            "year_desc": "a.start_year IS NULL, a.start_year DESC, a.name_uk",
            "year_asc": "a.start_year IS NULL, a.start_year ASC, a.name_uk",
        }.get(sort, "a.name_uk COLLATE NOCASE ASC")
        clause = f"WHERE {' AND '.join(where)}" if where else ""
        with self.database.connect() as connection:
            rows = connection.execute(
                f"SELECT a.* FROM artists a {clause} ORDER BY {order}", params
            ).fetchall()
            return [self._to_dict(connection, row) for row in rows]

    def get_artist(self, qid: str) -> dict[str, Any] | None:
        """Шукає одного виконавця за стабільним Wikidata QID."""
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM artists WHERE qid = ?", (qid,)).fetchone()
            return self._to_dict(connection, row) if row else None

    def genre_names(self) -> list[str]:
        """Повертає жанри для елемента фільтрації."""
        with self.database.connect() as connection:
            rows = connection.execute("SELECT name FROM genres ORDER BY name COLLATE NOCASE").fetchall()
            return [row[0] for row in rows]

    def stats(self) -> dict[str, Any]:
        """Обчислює кількісні показники для інформаційної панелі."""
        artists = self.list_artists()
        genres = Counter(genre["name"] for artist in artists for genre in artist["genres"])
        years = [artist["start_year"] for artist in artists if artist["start_year"]]
        with self.database.connect() as connection:
            metadata = {
                row["key"]: row["value"]
                for row in connection.execute("SELECT key, value FROM metadata").fetchall()
            }
        return {
            "artists": len(artists),
            "groups": sum(item["artist_type"] == "group" for item in artists),
            "persons": sum(item["artist_type"] == "person" for item in artists),
            "genres": len(genres),
            "earliest_year": min(years) if years else None,
            "top_genres": [
                {"name": name, "count": count} for name, count in genres.most_common(8)
            ],
            "metadata": metadata,
        }

