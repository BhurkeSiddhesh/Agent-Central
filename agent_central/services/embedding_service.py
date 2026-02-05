from __future__ import annotations

import datetime
import json
import os
from pathlib import Path
from typing import Dict, List, Optional


class EmbeddingService:
    def __init__(self, hq_path: Path):
        self.hq_path = Path(hq_path)
        self.embeddings_file = self.hq_path / "skills" / "skills.embeddings.json"
        self.model_name = os.getenv("SKILL_EMBED_MODEL", "all-MiniLM-L6-v2")
        self._model = None

    def _load_model(self):
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
        if not registry:
            skills = {}
            payload = {
                "model": self.model_name,
                "dimension": 0,
                "created_at": datetime.datetime.utcnow().isoformat(),
                "skills": skills,
            }
            self.embeddings_file.parent.mkdir(parents=True, exist_ok=True)
            self.embeddings_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            return skills

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
        existing = self.load_embeddings()
        if existing is not None:
            return existing
        return self.build_embeddings(registry)

    def embed_query(self, text: str) -> Optional[List[float]]:
        model = self._load_model()
        if model is None:
            return None
        try:
            vec = model.encode([text], normalize_embeddings=True)[0]
            return [float(v) for v in vec]
        except Exception as e:
            print(f"⚠️  Failed to embed query: {e}")
            return None
