"""Load config.yaml + cv.md, expose preferences and a cached CV embedding."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np
import yaml


@lru_cache(maxsize=1)
def _embedding_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer("all-MiniLM-L6-v2")


def embed(text: str) -> np.ndarray:
    model = _embedding_model()
    vec = model.encode(text, normalize_embeddings=True)
    return np.asarray(vec)


@dataclass
class Profile:
    cv_text: str
    cv_embedding: np.ndarray
    must_have: list[str]
    nice_to_have: list[str]
    exclude: list[str]
    remote_only: bool
    max_age_days: int
    countries: list[str]
    config: dict = field(default_factory=dict)


def load_profile(config_path: str = "config.yaml") -> Profile:
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))

    cv_path = Path(config["profile"]["cv_path"])
    cv_text = cv_path.read_text(encoding="utf-8")

    search = config.get("search", {})

    return Profile(
        cv_text=cv_text,
        cv_embedding=embed(cv_text),
        must_have=[s.lower() for s in search.get("must_have", [])],
        nice_to_have=[s.lower() for s in search.get("nice_to_have", [])],
        exclude=[s.lower() for s in search.get("exclude", [])],
        remote_only=search.get("remote_only", False),
        max_age_days=search.get("max_age_days", 30),
        countries=search.get("countries", []),
        config=config,
    )
