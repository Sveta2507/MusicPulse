"""JSON API для інтерфейсу та зовнішніх клієнтів."""

import re

from flask import Blueprint, abort, current_app, jsonify, request, send_file

from open_data import WikidataError


api = Blueprint("api", __name__, url_prefix="/api")


def _service():
    """Дістає сервіс зі сховища розширень Flask."""
    return current_app.extensions["music_service"]


@api.get("/health")
def health():
    """Спрощена перевірка готовності застосунку."""
    return jsonify(status="ok", artists=_service().repository.count())


@api.get("/artists")
def artists():
    """Пошук, фільтрація та сортування каталогу."""
    filters = {
        "search": request.args.get("search", "").strip()[:100],
        "genre": request.args.get("genre", "").strip()[:100],
        "artist_type": request.args.get("type", "").strip(),
        "sort": request.args.get("sort", "name").strip(),
    }
    items = _service().list_artists(**filters)
    return jsonify(items=items, count=len(items))


@api.get("/artists/<qid>")
def artist(qid: str):
    """Детальна інформація за QID."""
    if not re.fullmatch(r"Q\d+", qid):
        abort(400, description="Некоректний Wikidata QID")
    item = _service().get_artist(qid)
    if not item:
        abort(404, description="Виконавця не знайдено")
    return jsonify(item)


@api.get("/stats")
def stats():
    """Статистика каталогу та метадані джерела."""
    return jsonify(_service().stats())


@api.post("/refresh")
def refresh():
    """Запускає ручне оновлення Open Linked Data з Wikidata."""
    try:
        return jsonify(_service().refresh())
    except WikidataError as exc:
        return jsonify(status="error", message=str(exc)), 503


@api.get("/export/turtle")
def export_turtle_file():
    """Генерує і віддає RDF/Turtle-файл."""
    path, _ = _service().export_rdf()
    return send_file(path, as_attachment=True, download_name="ukrainian_music.ttl")

