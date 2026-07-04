"""Lightweight data models shared across the app."""
from dataclasses import dataclass, field


@dataclass
class Lead:
    company: str
    website: str
    email: str


@dataclass
class ScrapedSite:
    url: str
    pages_scraped: list = field(default_factory=list)
    content: str = ""
    success: bool = False
    error: str = ""


@dataclass
class GeneratedEmail:
    subject: str
    body: str
