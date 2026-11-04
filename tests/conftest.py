"""Спільне ізольоване оточення автоматичних тестів."""

from pathlib import Path

import pytest

from app import create_app


PROJECT_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture()
def application(tmp_path):
    """Створює застосунок із тимчасовою БД та готовим знімком."""
    app = create_app(
        {
            "TESTING": True,
            "DATABASE": tmp_path / "test.db",
            "SNAPSHOT_PATH": PROJECT_DIR / "data" / "wikidata_snapshot.json",
            "SEED_PATH": PROJECT_DIR / "data" / "seed_artists.json",
            "EXPORT_PATH": tmp_path / "test_export.ttl",
        }
    )
    return app


@pytest.fixture()
def client(application):
    """Повертає тестовий HTTP-клієнт Flask."""
    return application.test_client()


@pytest.fixture()
def service(application):
    """Повертає прикладний сервіс для модульних тестів."""
    return application.extensions["music_service"]

