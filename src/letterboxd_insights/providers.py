"""Metadata provider re-exports for extensibility."""

from .enrich import MetadataProvider, NullProvider, OMDbProvider

__all__ = ["MetadataProvider", "NullProvider", "OMDbProvider"]
