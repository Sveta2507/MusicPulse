"""Ініціалізація БД та RDF-експорту з наявного знімка."""

import sys
from pathlib import Path

# корінь додається до шляху імпорту, бо файл запускається безпосередньо з scripts/
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import create_app  # noqa: E402


def main() -> None:
    """Створює сховище і друкує контрольні кількісні результати."""
    application = create_app()
    service = application.extensions["music_service"]
    path, triples = service.export_rdf()
    stats = service.stats()
    print(f"Готово: {stats['artists']} виконавців, {stats['genres']} жанрів, {triples} RDF-трійок")
    print(f"Turtle: {path}")


if __name__ == "__main__":
    main()

