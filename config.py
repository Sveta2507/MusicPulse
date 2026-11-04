"""Налаштування застосунку та єдині шляхи до його ресурсів."""

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


class Config:
    """Базова конфігурація, яку можна замінити у тестах."""

    DATABASE = BASE_DIR / "instance" / "music.db"
    SNAPSHOT_PATH = BASE_DIR / "data" / "wikidata_snapshot.json"
    SEED_PATH = BASE_DIR / "data" / "seed_artists.json"
    EXPORT_PATH = BASE_DIR / "exports" / "ukrainian_music.ttl"
    IMAGE_DIR = BASE_DIR / "static" / "media"
    JSON_AS_ASCII = False
    SECRET_KEY = "local-development-key"

