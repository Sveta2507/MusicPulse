"""Перевірки семантичного експорту."""

from rdflib import Graph


def test_rdf_graph_is_valid_and_nonempty(service):
    path, expected_count = service.export_rdf()
    graph = Graph().parse(path, format="turtle")
    assert len(graph) == expected_count
    assert expected_count > 200


def test_rdf_contains_external_links(service):
    path, _ = service.export_rdf()
    text = path.read_text(encoding="utf-8")
    assert "https://www.wikidata.org/wiki/Q12071385" in text
    assert "owl:sameAs" in text


def test_rdf_does_not_publish_unverified_homepages(service):
    path, _ = service.export_rdf()
    text = path.read_text(encoding="utf-8")
    assert "foaf:homepage" not in text
    assert "brunettesshootblondes.org" not in text

