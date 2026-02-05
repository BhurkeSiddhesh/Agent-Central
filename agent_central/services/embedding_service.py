from __future__ import annotations

import datetime
import json
import os
from pathlib import Path
from typing import Dict, List, Optional


class EmbeddingService:
    def __init__(self, hq_path: Path):
        """
        Initialize the EmbeddingService with the HQ base path and configure embedding storage and model selection.
        
        Parameters:
            hq_path (Path): Base directory for HQ; the embeddings file will be <hq_path>/skills/skills.embeddings.json. The environment variable `SKILL_EMBED_MODEL` (default "all-MiniLM-L6-v2") is read to choose the embedding model. An internal model cache `_model` is initialized to None.
        """
        self.hq_path = Path(hq_path)
        self.embeddings_file = self.hq_path / "skills" / "skills.embeddings.json"
        self.model_name = os.getenv("SKILL_EMBED_MODEL", "all-MiniLM-L6-v2")
        self._model = None

    def _load_model(self):
        """
        Load and cache the SentenceTransformer model identified by `self.model_name`.
        
        Attempts to import and instantiate the sentence-transformers model, stores it on `self._model` for reuse, and returns it. Returns `None` if the sentence_transformers package is unavailable or if model instantiation fails.
        Returns:
            SentenceTransformer or None: The loaded model instance, or `None` if loading failed.
        """
        if self._model is not None:
            return self._model
        try:
            from sentence_transformers import SentenceTransformer
        except Exception as e:
            print(f"⚠️  sentence-transformers not available: {e}")
            return None
        try:
            self._model = SentenceTransformer(self.model_name)
            return self._model
        except Exception as e:
            print(f"⚠️  Failed to load embedding model '{self.model_name}': {e}")
            return None

    def load_embeddings(self) -> Optional[Dict[str, List[float]]]:
        """
        Load saved skill embeddings from the configured embeddings file if it exists and was created with the current model.
        
        Returns:
            dict: Mapping of skill id to embedding vector (list of floats) if a compatible, valid embeddings file is found; `None` otherwise.
        """
        if not self.embeddings_file.exists():
            return None
        try:
            payload = json.loads(self.embeddings_file.read_text(encoding="utf-8"))
        except Exception:
            return None
        if payload.get("model") != self.model_name:
            return None
        return payload.get("skills", {})

    def build_embeddings(self, registry: List[Dict]) -> Optional[Dict[str, List[float]]]:
        """
        Builds embeddings for the given skill registry and persists them to the service's embeddings file.
        
        Constructs a text representation for each skill, computes embeddings using the loaded model, writes a JSON payload with model metadata and the embeddings to self.embeddings_file, and returns a mapping of skill id to embedding vector.
        
        Parameters:
            registry (List[Dict]): Sequence of skill objects. Each skill must include an "id" key; optional keys like "name", "description", "tags", "domains", and "tech" are used when forming the text to embed.
        
        Returns:
            Optional[Dict[str, List[float]]]: A mapping from skill id to its embedding vector (list of floats), or `None` if the model cannot be loaded or embedding computation fails.
        """
        model = self._load_model()
        if model is None:
            return None

        texts = []
        ids = []
        for skill in registry:
            ids.append(skill["id"])
            text = " ".join(
                [
                    skill.get("name", ""),
                    skill.get("description", ""),
                    " ".join(skill.get("tags", [])),
                    " ".join(skill.get("domains", [])),
                    " ".join(skill.get("tech", [])),
                ]
            ).strip()
            texts.append(text or skill["id"])

        try:
            vectors = model.encode(texts, normalize_embeddings=True)
        except Exception as e:
            print(f"⚠️  Failed to compute embeddings: {e}")
            return None

        skills = {}
        for idx, vec in enumerate(vectors):
            skills[ids[idx]] = [float(v) for v in vec]

        payload = {
            "model": self.model_name,
            "dimension": len(vectors[0]) if len(vectors) > 0 else 0,
            "created_at": datetime.datetime.utcnow().isoformat(),
            "skills": skills,
        }
        self.embeddings_file.parent.mkdir(parents=True, exist_ok=True)
        self.embeddings_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return skills

    def load_or_build(self, registry: List[Dict]) -> Optional[Dict[str, List[float]]]:
        """
        Return existing skill embeddings from disk if present and valid; otherwise build embeddings from the provided registry.
        
        Parameters:
            registry (List[Dict]): List of skill records used to build embeddings when no valid cached embeddings are found.
        
        Returns:
            Optional[Dict[str, List[float]]]: Mapping from skill ID to embedding vector (list of floats), or `None` if embeddings could not be loaded or built.
        """
        existing = self.load_embeddings()
        if existing:
            return existing
        return self.build_embeddings(registry)

    def embed_query(self, text: str) -> Optional[List[float]]:
        """
        Create an embedding vector for the provided query text.
        
        Parameters:
            text (str): The query string to embed.
        
        Returns:
            embedding (Optional[List[float]]): A list of floats representing the normalized embedding for the query, or `None` if the embedding model is unavailable or embedding failed.
        """
        model = self._load_model()
        if model is None:
            return None
        try:
            vec = model.encode([text], normalize_embeddings=True)[0]
            return [float(v) for v in vec]
        except Exception as e:
            print(f"⚠️  Failed to embed query: {e}")
            return None