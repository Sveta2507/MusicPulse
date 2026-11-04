"""Точка входу вебзастосунку «UA Music Pulse»."""

from __future__ import annotations

from flask import Flask, jsonify, render_template

from config import Config
from data_access import ArtistRepository, Database
from open_data import WikidataClient, WikidataError
from routes.api import api
from routes.pages import pages
from services import MusicService


def create_app(test_config: dict | None = None) -> Flask:
    """Створює Flask-застосунок і з'єднує всі архітектурні шари."""
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    database = Database(app.config["DATABASE"])
    database.initialize()
    repository = ArtistRepository(database)
    client = WikidataClient(app.config["SEED_PATH"])
    service = MusicService(
        repository,
        client,
        app.config["SNAPSHOT_PATH"],
        app.config["EXPORT_PATH"],
    )
    try:
        service.bootstrap()
    except WikidataError:
        if not app.config.get("TESTING"):
            raise

    app.extensions["music_service"] = service
    app.register_blueprint(pages)
    app.register_blueprint(api)

    @app.errorhandler(404)
    def not_found(error):
        if str(getattr(error, "description", "")).startswith("Виконавця"):
            return jsonify(error=error.description), 404
        return render_template("404.html"), 404

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify(error=getattr(error, "description", "Некоректний запит")), 400

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)

