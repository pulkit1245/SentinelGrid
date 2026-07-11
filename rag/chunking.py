import os
from typing import List, Dict, Any
from PyPDF2 import PdfReader

class DocumentChunker:
    """
    Splits documents (PDFs) into structural chunks (roughly 300-500 tokens) 
    with a sliding context overlap and metadata tagging.
    """
    def __init__(self, chunk_size: int = 400, overlap: int = 60):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def _split_text(self, text: str) -> List[str]:
        # Simple word-based splitting for MVP
        words = text.split()
        chunks = []
        i = 0
        while i < len(words):
            chunk = " ".join(words[i:i + self.chunk_size])
            chunks.append(chunk)
            i += self.chunk_size - self.overlap
        return chunks

    def chunk_pdf(self, filepath: str) -> List[Dict[str, Any]]:
        filename = os.path.basename(filepath)
        print(f"Parsing PDF: {filename}...")
        
        try:
            reader = PdfReader(filepath)
            content = ""
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    content += text + "\n"
        except Exception as e:
            print(f"Error reading PDF {filename}: {e}")
            return []

        chunks = self._split_text(content)
        
        chunk_dicts = []
        for idx, text in enumerate(chunks):
            doc_id = filename.replace('.pdf', '')
            
            chunk_dicts.append({
                "id": f"{doc_id}_chunk_{idx}",
                "text": text,
                "metadata": {
                    "source_type": "pdf_document",
                    "document_id": doc_id,
                    "chunk_index": idx,
                    "filepath": filepath
                }
            })
            
        return chunk_dicts

    def process_corpus(self, corpus_dir: str) -> List[Dict[str, Any]]:
        all_chunks = []
        
        if os.path.exists(corpus_dir):
            for file in os.listdir(corpus_dir):
                if file.lower().endswith('.pdf'):
                    filepath = os.path.join(corpus_dir, file)
                    all_chunks.extend(self.chunk_pdf(filepath))
                    
        return all_chunks

if __name__ == "__main__":
    chunker = DocumentChunker()
    chunks = chunker.process_corpus(os.path.join(os.path.dirname(__file__), "corpus"))
    print(f"Processed {len(chunks)} chunks.")
