"""
rag.py
Retrieval-Augmented Generation pipeline for payer policy retrieval.
Chunks policy documents, embeds them, stores in ChromaDB,
and retrieves relevant policy context for each PA case.

Usage:
    from src.rag import RAGPipeline
    rag = RAGPipeline()
    rag.load_policies(policy_docs)
    chunks = rag.retrieve(case, top_k=3)
"""

import json
import warnings
from pathlib import Path
from typing import List, Dict, Optional

import numpy as np

warnings.filterwarnings('ignore')


def chunk_document(doc: dict, chunk_size: int = 150, overlap: int = 30) -> List[dict]:
    """
    Split a policy document into overlapping word-level chunks.

    Args:
        doc:        dict with keys doc_id, source, category, text
        chunk_size: target words per chunk
        overlap:    words shared between adjacent chunks
    Returns:
        List of chunk dicts
    """
    words  = doc['text'].split()
    chunks = []
    start  = 0
    idx    = 0
    while start < len(words):
        end  = min(start + chunk_size, len(words))
        text = ' '.join(words[start:end]).strip()
        if len(text) > 50:
            chunks.append({
                'chunk_id':   f'{doc["doc_id"]}_chunk_{idx:03d}',
                'doc_id':     doc['doc_id'],
                'source':     doc['source'],
                'category':   doc['category'],
                'text':       text,
                'word_count': end - start,
            })
            idx += 1
        start += chunk_size - overlap
    return chunks


def build_query(case: dict) -> str:
    """
    Build a retrieval query from extracted case signals.
    Combines clinical category, ICD codes, and note prefix.
    """
    ext   = case.get('predicted_extraction', {})
    parts = [
        case.get('clinical_category', '').replace('_', ' '),
        ' '.join(ext.get('diagnoses', [])),
        case.get('note', '')[:300],
    ]
    return ' '.join(p for p in parts if p).strip()


class RAGPipeline:
    """
    Full RAG pipeline: ingest → embed → store → retrieve.

    Falls back to keyword overlap scoring if sentence-transformers
    or ChromaDB are not installed.
    """

    def __init__(self, chunk_size: int = 150, overlap: int = 30):
        self.chunk_size  = chunk_size
        self.overlap     = overlap
        self.all_chunks  = []
        self.embeddings  = None
        self.collection  = None

        # Try loading embedding model
        try:
            from sentence_transformers import SentenceTransformer
            self.embed_model        = SentenceTransformer('all-MiniLM-L6-v2')
            self.use_embeddings     = True
        except ImportError:
            self.embed_model        = None
            self.use_embeddings     = False

        # Try loading ChromaDB
        try:
            import chromadb
            client = chromadb.Client()
            try:
                client.delete_collection('payer_policies')
            except Exception:
                pass
            self.collection = client.create_collection(
                name='payer_policies',
                metadata={'hnsw:space': 'cosine'}
            )
            self.use_chroma = True
        except ImportError:
            self.use_chroma = False

    def load_policies(self, policy_docs: List[dict]) -> None:
        """Chunk, embed, and index a list of policy documents."""
        self.all_chunks = []
        for doc in policy_docs:
            self.all_chunks.extend(
                chunk_document(doc, self.chunk_size, self.overlap)
            )

        if self.use_embeddings:
            texts            = [c['text'] for c in self.all_chunks]
            self.embeddings  = self.embed_model.encode(texts)

            if self.use_chroma:
                self.collection.add(
                    ids        = [c['chunk_id'] for c in self.all_chunks],
                    documents  = [c['text']     for c in self.all_chunks],
                    embeddings = self.embeddings.tolist(),
                    metadatas  = [{
                        'doc_id':   c['doc_id'],
                        'source':   c['source'],
                        'category': c['category'],
                    } for c in self.all_chunks]
                )
        else:
            # Simulate embeddings for testing
            n                = len(self.all_chunks)
            self.embeddings  = np.random.randn(n, 384)
            self.embeddings /= np.linalg.norm(self.embeddings, axis=1, keepdims=True)

    def load_pdfs(self, folder: str) -> None:
        """
        Load real payer policy PDFs from a folder.
        Requires PyPDF2: pip install pypdf2
        """
        try:
            import PyPDF2
        except ImportError:
            raise ImportError('Install PyPDF2 to load PDFs: pip install pypdf2')

        docs = []
        for pdf_path in Path(folder).glob('*.pdf'):
            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text   = ' '.join(
                    page.extract_text() for page in reader.pages
                    if page.extract_text()
                )
            docs.append({
                'doc_id':   pdf_path.stem,
                'source':   pdf_path.name,
                'category': 'general',
                'text':     text,
            })
            print(f'Loaded: {pdf_path.name}  ({len(text.split())} words)')
        self.load_policies(docs)

    def retrieve(self, case: dict, top_k: int = 3) -> List[dict]:
        """
        Retrieve top-K most relevant policy chunks for a PA case.

        Returns:
            List of chunk dicts with chunk_id, source, text, distance
        """
        query = build_query(case)

        if self.use_embeddings and self.use_chroma:
            q_embed = self.embed_model.encode([query]).tolist()
            results = self.collection.query(
                query_embeddings=q_embed,
                n_results=top_k
            )
            return [{
                'chunk_id': results['ids'][0][i],
                'source':   results['metadatas'][0][i]['source'],
                'text':     results['documents'][0][i],
                'distance': results['distances'][0][i],
            } for i in range(len(results['ids'][0]))]

        else:
            # Keyword overlap fallback
            query_words = set(query.lower().split())
            scores = sorted(
                [(len(query_words & set(c['text'].lower().split())), c)
                 for c in self.all_chunks],
                key=lambda x: x[0], reverse=True
            )
            return [{
                'chunk_id': c['chunk_id'],
                'source':   c['source'],
                'text':     c['text'],
                'distance': round(1 - s / max(len(query_words), 1), 3)
            } for s, c in scores[:top_k]]

    def build_policy_context(self, chunks: List[dict]) -> str:
        """Format retrieved chunks into a single policy context string."""
        return '\n\n'.join(
            f'[Source: {c["source"]}]\n{c["text"]}' for c in chunks
        )

    def enrich_case(self, case: dict, top_k: int = 3) -> dict:
        """Add retrieved policy context to a case dict."""
        chunks = self.retrieve(case, top_k=top_k)
        return {
            **case,
            'retrieved_policy_chunks': chunks,
            'policy_context':          self.build_policy_context(chunks),
            'retrieved_sources':       [c['source'] for c in chunks],
        }

    def enrich_batch(self, cases: list, top_k: int = 3) -> list:
        """Enrich a list of cases with policy context."""
        return [self.enrich_case(c, top_k) for c in cases]
