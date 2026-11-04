"""Модуль отримання відкритих пов'язаних даних."""

from .wikidata_client import WikidataClient, WikidataError

__all__ = ["WikidataClient", "WikidataError"]

