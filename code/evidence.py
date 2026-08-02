from __future__ import annotations

import math
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from code.schemas import MessageHistoryRow


@dataclass(frozen=True)
class EvidenceIndex:
    user_id: str
    documents: tuple[MessageHistoryRow, ...]
    bm25_index: dict[str, dict[str, float]]
    vector_index: dict[str, dict[str, float]]
    document_ids: tuple[str, ...]


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    value = value.lower()
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _tokenize(value: str | None) -> list[str]:
    normalized = _normalize_text(value)
    return normalized.split() if normalized else []


def _build_bm25_index(documents: Iterable[MessageHistoryRow]) -> dict[str, dict[str, float]]:
    docs = list(documents)
    if not docs:
        return {}

    token_docs: list[list[str]] = []
    for doc in docs:
        tokens = _tokenize(doc.message_text)
        token_docs.append(tokens)

    doc_freqs: dict[str, int] = defaultdict(int)
    for tokens in token_docs:
        unique_tokens = set(tokens)
        for token in unique_tokens:
            doc_freqs[token] += 1

    total_docs = len(docs)
    index: dict[str, dict[str, float]] = {}
    for doc_idx, doc in enumerate(docs):
        tokens = token_docs[doc_idx]
        if not tokens:
            continue
        tf = defaultdict(float)
        for token in tokens:
            tf[token] += 1.0
        score_map: dict[str, float] = {}
        for token, count in tf.items():
            idf = math.log((1 + (total_docs - doc_freqs[token] + 0.5)) / (0.5 + doc_freqs[token]) + 1.0)
            score_map[token] = count * idf
        index[doc.message_id] = score_map
    return index


def _build_vector_index(documents: Iterable[MessageHistoryRow]) -> dict[str, dict[str, float]]:
    vector_index: dict[str, dict[str, float]] = {}
    for doc in documents:
        tokens = _tokenize(doc.message_text)
        if not tokens:
            continue
        counts = defaultdict(float)
        for token in tokens:
            counts[token] += 1.0
        total_weight = sum(counts.values())
        if total_weight == 0:
            continue
        vector = {token: count / total_weight for token, count in counts.items()}
        vector_index[doc.message_id] = vector
    return vector_index


def build_evidence_index(history_rows: Iterable[MessageHistoryRow], user_id: str | None = None) -> EvidenceIndex:
    docs = list(history_rows)
    if user_id is None:
        user_id = docs[0].user_id if docs else ""
    docs = [doc for doc in docs if doc.user_id == user_id] if user_id else docs
    return EvidenceIndex(
        user_id=user_id or "",
        documents=tuple(docs),
        bm25_index=_build_bm25_index(docs),
        vector_index=_build_vector_index(docs),
        document_ids=tuple(doc.message_id for doc in docs),
    )


def _token_overlap_score(query_tokens: list[str], document_vector: dict[str, float]) -> float:
    if not query_tokens:
        return 0.0
    matches = sum(1 for token in query_tokens if token in document_vector)
    return matches / max(len(query_tokens), 1)


def _cosine_similarity(query_tokens: list[str], document_vector: dict[str, float]) -> float:
    if not query_tokens:
        return 0.0
    if not document_vector:
        return 0.0
    query_vector = defaultdict(float)
    for token in query_tokens:
        query_vector[token] += 1.0
    magnitude_query = math.sqrt(sum(value * value for value in query_vector.values()))
    magnitude_doc = math.sqrt(sum(value * value for value in document_vector.values()))
    if magnitude_query == 0 or magnitude_doc == 0:
        return 0.0
    numerator = sum(query_vector[token] * weight for token, weight in document_vector.items() if token in query_vector)
    denominator = magnitude_query * magnitude_doc
    if denominator == 0:
        return 0.0
    return numerator / denominator


def retrieve_evidence(index: EvidenceIndex, user_id: str, query_text: str, top_k: int = 5) -> list[str]:
    if not query_text or top_k <= 0:
        return []

    query_tokens = _tokenize(query_text)
    if not query_tokens:
        return []

    document_lookup = {doc.message_id: doc for doc in index.documents}
    scored: list[tuple[float, str]] = []
    for doc_id in index.document_ids:
        document = document_lookup.get(doc_id)
        if document is None:
            continue
        bm25_score = sum(index.bm25_index.get(doc_id, {}).get(token, 0.0) for token in query_tokens)
        semantic_score = _cosine_similarity(query_tokens, index.vector_index.get(doc_id, {}))
        lexical_score = _token_overlap_score(query_tokens, index.vector_index.get(doc_id, {}))
        combined_score = bm25_score + semantic_score + lexical_score
        scored.append((combined_score, doc_id))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [message_id for _, message_id in scored[:top_k]]
