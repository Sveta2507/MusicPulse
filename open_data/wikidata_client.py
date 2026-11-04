"""Клієнт Wikidata Query Service для одержання Open Linked Data."""

from __future__ import annotations

import json
import re
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


class WikidataError(RuntimeError):
    """Помилка читання або розбору даних Wikidata."""


class WikidataClient:
    """Завантажує описи відібраних українських музичних виконавців."""

    endpoint = "https://query.wikidata.org/sparql"

    def __init__(self, seed_path: Path, timeout: int = 35) -> None:
        self.seed_path = Path(seed_path)
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "UAMusicPulse/1.0 (educational semantic-web project)",
                "Accept": "application/sparql-results+json",
            }
        )

    def _seeds(self) -> list[dict[str, Any]]:
        """Читає кураторський список сутностей та резервні назви жанрів."""
        return json.loads(self.seed_path.read_text(encoding="utf-8"))

    def _query(self, qids: list[str]) -> str:
        """Формує SPARQL-запит з VALUES, не вставляючи довільний ввід користувача."""
        values = " ".join(f"wd:{qid}" for qid in qids)
        return f"""
PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX schema: <http://schema.org/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?item ?nameUk ?nameEn ?descriptionUk ?descriptionEn ?image
       ?inception ?birthDate ?genre ?genreUk ?genreEn ?instance ?spotifyId ?youtubeId
WHERE {{
  VALUES ?item {{ {values} }}
  OPTIONAL {{ ?item rdfs:label ?nameUk. FILTER(LANG(?nameUk) = "uk") }}
  OPTIONAL {{ ?item rdfs:label ?nameEn. FILTER(LANG(?nameEn) = "en") }}
  OPTIONAL {{ ?item schema:description ?descriptionUk. FILTER(LANG(?descriptionUk) = "uk") }}
  OPTIONAL {{ ?item schema:description ?descriptionEn. FILTER(LANG(?descriptionEn) = "en") }}
  OPTIONAL {{ ?item wdt:P18 ?image }}
  OPTIONAL {{ ?item wdt:P571 ?inception }}
  OPTIONAL {{ ?item wdt:P569 ?birthDate }}
  OPTIONAL {{
    ?item wdt:P136 ?genre.
    OPTIONAL {{ ?genre rdfs:label ?genreUk. FILTER(LANG(?genreUk) = "uk") }}
    OPTIONAL {{ ?genre rdfs:label ?genreEn. FILTER(LANG(?genreEn) = "en") }}
  }}
  OPTIONAL {{ ?item wdt:P31 ?instance }}
  OPTIONAL {{ ?item wdt:P1902 ?spotifyId }}
  OPTIONAL {{ ?item wdt:P2397 ?youtubeId }}
}}
ORDER BY ?item ?genre
""".strip()

    @staticmethod
    def _value(row: dict[str, Any], key: str) -> str | None:
        """Безпечно дістає текстове значення зі SPARQL JSON binding."""
        return row.get(key, {}).get("value")

    @staticmethod
    def _year(value: str | None) -> int | None:
        """Перетворює дату xsd:dateTime на рік."""
        if not value:
            return None
        match = re.match(r"^([+-]?\d{4,})", value)
        return int(match.group(1)) if match else None

    def fetch_artists(self) -> dict[str, Any]:
        """Пакетно виконує SPARQL-запити й нормалізує великий набір результатів."""
        seeds = self._seeds()
        seed_by_qid = {item["qid"]: item for item in seeds}
        rows: list[dict[str, Any]] = []
        qids = list(seed_by_qid)
        # невеликі пакети не перевантажують WDQS і не створюють надто довгі URL
        for offset in range(0, len(qids), 35):
            batch = qids[offset : offset + 35]
            last_error: Exception | None = None
            for attempt in range(3):
                try:
                    response = self.session.get(
                        self.endpoint,
                        params={"query": self._query(batch), "format": "json"},
                        timeout=self.timeout,
                    )
                    response.raise_for_status()
                    rows.extend(response.json()["results"]["bindings"])
                    last_error = None
                    break
                except (requests.RequestException, KeyError, ValueError) as exc:
                    last_error = exc
                    time.sleep(2 * (attempt + 1))
            if last_error:
                raise WikidataError(f"Не вдалося отримати дані Wikidata: {last_error}") from last_error
            time.sleep(0.4)

        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            item_uri = self._value(row, "item") or ""
            qid = item_uri.rsplit("/", 1)[-1]
            if qid in seed_by_qid:
                grouped[qid].append(row)

        retrieved_at = datetime.now(timezone.utc).isoformat()
        artists: list[dict[str, Any]] = []
        for qid, seed in seed_by_qid.items():
            entity_rows = grouped.get(qid, [])
            first = entity_rows[0] if entity_rows else {}
            genre_map: dict[str, str] = {}
            for row in entity_rows:
                genre_uri = self._value(row, "genre")
                if genre_uri:
                    genre_id = genre_uri.rsplit("/", 1)[-1]
                    genre_map[genre_id] = (
                        self._value(row, "genreUk")
                        or self._value(row, "genreEn")
                        or genre_id
                    )
            if not genre_map:
                genre_map = {
                    f"local:{self._slug(name)}": name for name in seed.get("genres", [])
                }

            instances = {
                (self._value(row, "instance") or "").rsplit("/", 1)[-1]
                for row in entity_rows
            }
            spotify_id = self._value(first, "spotifyId")
            youtube_id = self._value(first, "youtubeId")
            artists.append(
                {
                    "qid": qid,
                    "name_uk": self._value(first, "nameUk")
                    or self._value(first, "nameEn")
                    or seed["name_uk"],
                    "name_en": self._value(first, "nameEn")
                    or self._value(first, "nameUk")
                    or seed["name_en"],
                    "description": self._value(first, "descriptionUk")
                    or self._value(first, "descriptionEn")
                    or "представник сучасної української музичної сцени",
                    "artist_type": "person" if "Q5" in instances else seed["kind"],
                    "start_year": self._year(self._value(first, "inception"))
                    or self._year(self._value(first, "birthDate")),
                    "image_url": self._value(first, "image"),
                    "wikidata_url": f"https://www.wikidata.org/wiki/{qid}",
                    "spotify_url": f"https://open.spotify.com/artist/{spotify_id}"
                    if spotify_id
                    else None,
                    "youtube_url": f"https://www.youtube.com/channel/{youtube_id}"
                    if youtube_id
                    else None,
                    "genres": [
                        {"id": genre_id, "name": name}
                        for genre_id, name in sorted(genre_map.items(), key=lambda item: item[1])
                    ],
                    "retrieved_at": retrieved_at,
                }
            )

        return {
            "source": self.endpoint,
            "license": "CC0 1.0",
            "retrieved_at": retrieved_at,
            "query": self._query(list(seed_by_qid)),
            "artists": artists,
        }

    @staticmethod
    def _slug(text: str) -> str:
        """Створює стабільний локальний ідентифікатор для резервного жанру."""
        return re.sub(r"[^a-z0-9а-яіїєґ]+", "-", text.lower()).strip("-")

    @staticmethod
    def save_snapshot(payload: dict[str, Any], path: Path) -> None:
        """Зберігає відповідь для автономного запуску без мережі."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

