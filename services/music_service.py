"""Бізнес-логіка каталогу сучасної української музики."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from data_access import ArtistRepository
from open_data import WikidataClient, WikidataError

from .rdf_export import export_turtle


class MusicService:
    """Координує зовнішні дані, репозиторій та RDF-експорт."""

    def __init__(
        self,
        repository: ArtistRepository,
        client: WikidataClient,
        snapshot_path: Path,
        export_path: Path,
    ) -> None:
        self.repository = repository
        self.client = client
        self.snapshot_path = Path(snapshot_path)
        self.export_path = Path(export_path)

    def bootstrap(self) -> str:
        """Заповнює порожню БД локальним знімком або Wikidata."""
        if self.repository.count():
            return "database"
        if self.snapshot_path.exists():
            payload = json.loads(self.snapshot_path.read_text(encoding="utf-8"))
            self.repository.replace_all(payload)
            return "snapshot"
        payload = self.client.fetch_artists()
        self.client.save_snapshot(payload, self.snapshot_path)
        self.repository.replace_all(payload)
        return "wikidata"

    def refresh(self) -> dict[str, Any]:
        """Оновлює дані з Wikidata; за помилки залишає чинну БД без змін."""
        payload = self.client.fetch_artists()
        self.client.save_snapshot(payload, self.snapshot_path)
        self.repository.replace_all(payload)
        path, triple_count = self.export_rdf()
        return {
            "status": "ok",
            "artists": len(payload["artists"]),
            "triples": triple_count,
            "export": str(path),
            "retrieved_at": payload["retrieved_at"],
        }

    def list_artists(self, **filters: str) -> list[dict[str, Any]]:
        """Передає безпечні параметри пошуку репозиторію."""
        return self.repository.list_artists(**filters)

    def get_artist(self, qid: str) -> dict[str, Any] | None:
        """Повертає картку виконавця."""
        return self.repository.get_artist(qid)

    def stats(self) -> dict[str, Any]:
        """Повертає агреговану статистику."""
        return self.repository.stats()

    def export_rdf(self) -> tuple[Path, int]:
        """Створює Turtle-файл із семантичними зв'язками owl:sameAs."""
        stats = self.repository.stats()
        source = stats["metadata"].get("source", WikidataClient.endpoint)
        return export_turtle(self.repository.list_artists(), source, self.export_path)


__all__ = ["MusicService", "WikidataError"]

