"""Перетворення локальних даних у семантичний RDF-граф."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import quote

from rdflib import DCTERMS, OWL, RDF, Graph, Literal, Namespace, URIRef
from rdflib.namespace import XSD


SCHEMA = Namespace("https://schema.org/")
MUSIC = Namespace("https://svitlana-denysenko.github.io/ua-music/resource/")


def build_graph(artists: list[dict[str, Any]], source: str) -> Graph:
    """Будує RDF-трійки про виконавців, жанри та зв'язки з Wikidata."""
    graph = Graph()
    graph.bind("schema", SCHEMA)
    graph.bind("music", MUSIC)
    graph.bind("owl", OWL)
    graph.bind("dcterms", DCTERMS)

    dataset = MUSIC["dataset/modern-ukrainian-music"]
    graph.add((dataset, RDF.type, SCHEMA.Dataset))
    graph.add((dataset, DCTERMS.title, Literal("Сучасний музичний світ України", lang="uk")))
    graph.add((dataset, DCTERMS.source, URIRef(source)))
    graph.add((dataset, DCTERMS.license, URIRef("https://creativecommons.org/publicdomain/zero/1.0/")))

    for artist in artists:
        resource = MUSIC[f"artist/{artist['qid']}"]
        entity_type = SCHEMA.Person if artist["artist_type"] == "person" else SCHEMA.MusicGroup
        graph.add((resource, RDF.type, entity_type))
        graph.add((resource, SCHEMA.name, Literal(artist["name_uk"], lang="uk")))
        graph.add((resource, SCHEMA.alternateName, Literal(artist["name_en"], lang="en")))
        graph.add((resource, SCHEMA.description, Literal(artist["description"], lang="uk")))
        graph.add((resource, OWL.sameAs, URIRef(artist["wikidata_url"])))
        graph.add((dataset, SCHEMA.about, resource))
        if artist.get("start_year"):
            date_property = SCHEMA.birthDate if artist["artist_type"] == "person" else SCHEMA.foundingDate
            graph.add((resource, date_property, Literal(artist["start_year"], datatype=XSD.gYear)))
        if artist.get("image_url"):
            graph.add((resource, SCHEMA.image, URIRef(artist["image_url"])))
        for genre in artist.get("genres", []):
            genre_key = quote(genre["id"].replace(":", "-"), safe="")
            genre_resource = MUSIC[f"genre/{genre_key}"]
            graph.add((genre_resource, RDF.type, SCHEMA.MusicGenre))
            graph.add((genre_resource, SCHEMA.name, Literal(genre["name"], lang="uk")))
            graph.add((resource, SCHEMA.genre, genre_resource))
    return graph


def export_turtle(artists: list[dict[str, Any]], source: str, path: Path) -> tuple[Path, int]:
    """Серіалізує RDF-граф у Turtle і повертає кількість трійок."""
    graph = build_graph(artists, source)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(destination=path, format="turtle")
    return path, len(graph)

