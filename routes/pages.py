"""Маршрути HTML-сторінок."""

from flask import Blueprint, current_app, render_template


pages = Blueprint("pages", __name__)


@pages.get("/")
def index():
    """Відображає основний каталог."""
    service = current_app.extensions["music_service"]
    return render_template(
        "index.html",
        stats=service.stats(),
        genres=service.repository.genre_names(),
    )


@pages.get("/about")
def about():
    """Пояснює джерела, архітектуру та семантику проєкту."""
    service = current_app.extensions["music_service"]
    return render_template("about.html", stats=service.stats())

