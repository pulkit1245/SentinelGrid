import os
import json
import math
from typing import List, Dict, Any
from collections import defaultdict

class BM25SparseIndexer:
    """
    Localized BM25 sparse keyword parser for exact statutory code matching.
    """
    def __init__(self):
        self.documents = []
        self.doc_freqs = defaultdict(int)
        self.idf = {}
        self.doc_lengths = []
        self.avgdl = 0
        self.k1 = 1.5
        self.b = 0.75

    def _tokenize(self, text: str) -> List[str]:
        return text.lower().replace('.', ' ').replace(',', ' ').split()

    def build_index(self, chunks: List[Dict[str, Any]]):
        self.documents = chunks
        self.doc_lengths = []
        self.doc_freqs.clear()
        
        doc_word_counts = []
        for chunk in chunks:
            tokens = self._tokenize(chunk["text"])
            self.doc_lengths.append(len(tokens))
            
            word_count = defaultdict(int)
            for token in tokens:
                word_count[token] += 1
            doc_word_counts.append(word_count)
            
            for word in word_count.keys():
                self.doc_freqs[word] += 1
                
        N = len(self.documents)
        self.avgdl = sum(self.doc_lengths) / max(1, N)
        
        # Calculate IDF
        self.idf = {}
        for word, freq in self.doc_freqs.items():
            self.idf[word] = math.log(1 + (N - freq + 0.5) / (freq + 0.5))

        self.doc_word_counts = doc_word_counts
        print(f"Built BM25 index over {N} documents.")

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        tokens = self._tokenize(query)
        scores = []
        
        for i in range(len(self.documents)):
            score = 0
            doc_len = self.doc_lengths[i]
            word_counts = self.doc_word_counts[i]
            
            for token in tokens:
                if token not in word_counts:
                    continue
                tf = word_counts[token]
                idf = self.idf.get(token, 0)
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * (doc_len / max(1, self.avgdl)))
                score += idf * (numerator / denominator)
                
            scores.append((score, i))
            
        scores.sort(key=lambda x: x[0], reverse=True)
        
        results = []
        for score, i in scores[:limit]:
            if score > 0:
                results.append({
                    "score": score,
                    "payload": {
                        "text": self.documents[i]["text"],
                        **self.documents[i]["metadata"]
                    }
                })
        return results

if __name__ == "__main__":
    from rag.chunking import DocumentChunker
    from rag.embeddings import VectorDatabaseBuilder

    print("=== Starting Reindexing Pipeline ===")
    chunker = DocumentChunker()
    corpus_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "corpus")
    chunks = chunker.process_corpus(corpus_dir)
    
    print("Building Qdrant Vector Index...")
    qdrant_url = os.environ.get("QDRANT_URL", "http://localhost:6333")
    qdrant_path = os.environ.get("QDRANT_PATH")
    try:
        vector_db = VectorDatabaseBuilder(qdrant_url=qdrant_url, qdrant_path=qdrant_path)
        vector_db.embed_and_index(chunks)
    except Exception as e:
        print(f"Warning: Could not build Qdrant index ({e}). BM25-only mode.")

    print("Building BM25 Sparse Index...")
    bm25 = BM25SparseIndexer()
    bm25.build_index(chunks)
    
    # Save BM25 index to disk (mock approach: just save chunks to a json file to rebuild on load)
    index_path = os.path.join(os.path.dirname(__file__), "bm25_store.json")
    with open(index_path, 'w') as f:
        json.dump(chunks, f)
    print(f"BM25 chunks saved to {index_path}")
    print("=== Reindexing Complete ===")
