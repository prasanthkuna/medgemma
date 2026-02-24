"""
Policy RAG Service
FAISS-based retrieval with citations
"""
from pathlib import Path
from typing import List, Dict, Any
import logging
import json

from config import settings

logger = logging.getLogger(__name__)


async def index_policy(payer_id: str, pdf_files: List[Path]) -> Path:
    """
    Build FAISS index for policy documents
    
    Args:
        payer_id: Payer identifier
        pdf_files: List of PDF file paths
        
    Returns:
        Path to the FAISS index
    """
    import faiss
    import numpy as np
    import pdfplumber
    import ollama
    
    index_dir = settings.policies_dir / payer_id / "faiss_index"
    index_dir.mkdir(parents=True, exist_ok=True)
    
    chunks = []
    metadata = []
    
    # Extract and chunk text from PDFs
    for pdf_path in pdf_files:
        logger.info(f"Processing policy: {pdf_path.name}")
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text() or ""
                    
                    # Chunk by paragraphs (simple approach)
                    page_chunks = _chunk_text(text, max_tokens=500, overlap=50)
                    
                    for i, chunk in enumerate(page_chunks):
                        if len(chunk.strip()) > 50:  # Skip very short chunks
                            chunks.append(chunk)
                            metadata.append({
                                "pdf_name": pdf_path.name,
                                "page_num": page_num,
                                "chunk_id": f"{pdf_path.stem}_p{page_num}_c{i}",
                                "text": chunk
                            })
        except Exception as e:
            logger.error(f"Error processing {pdf_path}: {e}")
    
    if not chunks:
        raise ValueError("No text extracted from policy documents")
    
    # Generate embeddings using Ollama
    logger.info(f"Generating embeddings for {len(chunks)} chunks...")
    embeddings = []
    
    for chunk in chunks:
        try:
            response = ollama.embeddings(
                model=settings.embedding_model,
                prompt=chunk
            )
            embeddings.append(response["embedding"])
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            # Use zero vector as fallback
            embeddings.append([0.0] * 768)
    
    # Build FAISS index for Cosine Similarity
    embeddings_array = np.array(embeddings).astype('float32')
    faiss.normalize_L2(embeddings_array)
    dimension = embeddings_array.shape[1]
    
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings_array)
    
    # Save index and metadata
    index_path = index_dir / "index.faiss"
    faiss.write_index(index, str(index_path))
    
    metadata_path = index_dir / "metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    
    logger.info(f"Index built with {len(chunks)} chunks at {index_path}")
    
    return index_dir


async def index_policy_stream(payer_id: str, pdf_files: List[Path]):
    """
    Build FAISS index for policy documents and yield progress logs (Generator)
    """
    import faiss
    import numpy as np
    import pdfplumber
    import ollama
    
    index_dir = settings.policies_dir / payer_id / "faiss_index"
    index_dir.mkdir(parents=True, exist_ok=True)
    
    chunks = []
    metadata = []
    
    yield {"step": "parsing", "message": f"Initializing parsing for {len(pdf_files)} PDF(s)..."}
    
    # Extract and chunk text from PDFs
    for pdf_path in pdf_files:
        yield {"step": "parsing", "message": f"Extracting text from: {pdf_path.name}"}
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text() or ""
                    page_chunks = _chunk_text(text, max_tokens=500, overlap=50)
                    
                    for i, chunk in enumerate(page_chunks):
                        if len(chunk.strip()) > 50:
                            chunks.append(chunk)
                            metadata.append({
                                "pdf_name": pdf_path.name,
                                "page_num": page_num,
                                "chunk_id": f"{pdf_path.stem}_p{page_num}_c{i}",
                                "text": chunk
                            })
                    if page_num % 5 == 0:
                        yield {"step": "parsing", "message": f"Processed {page_num} pages of {pdf_path.name}"}
        except Exception as e:
            logger.error(f"Error processing {pdf_path}: {e}")
            yield {"step": "error", "message": f"Error parsing {pdf_path.name}: {str(e)}"}
    
    if not chunks:
        yield {"step": "error", "message": "No valid text chunks found in documents."}
        return

    # Generate embeddings
    yield {"step": "embedding", "message": f"Generating embeddings for {len(chunks)} chunks via {settings.embedding_model}..."}
    embeddings = []
    
    for idx, chunk in enumerate(chunks):
        try:
            response = ollama.embeddings(
                model=settings.embedding_model,
                prompt=chunk
            )
            embeddings.append(response["embedding"])
            
            if (idx + 1) % 10 == 0 or (idx + 1) == len(chunks):
                yield {
                    "step": "embedding", 
                    "message": f"Vectorizing chunks: {idx+1}/{len(chunks)} complete",
                    "progress": round((idx + 1) / len(chunks) * 100, 1)
                }
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            embeddings.append([0.0] * 768)

    # Build FAISS index
    yield {"step": "faiss", "message": "Constructing FAISS index with L2 Normalization..."}
    embeddings_array = np.array(embeddings).astype('float32')
    faiss.normalize_L2(embeddings_array)
    dimension = embeddings_array.shape[1]
    
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings_array)
    
    # Save index and metadata
    index_path = index_dir / "index.faiss"
    faiss.write_index(index, str(index_path))
    
    metadata_path = index_dir / "metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    
    yield {
        "step": "complete", 
        "message": "Policy Vectorization Complete.", 
        "index_path": str(index_dir),
        "chunks": len(chunks)
    }


async def search_policy(index_dir: Path, query: str, k: int = 5) -> List[Dict[str, Any]]:
    """
    Search policy documents with citations
    
    Args:
        index_dir: Path to FAISS index directory
        query: Search query
        k: Number of results
        
    Returns:
        List of results with citations
    """
    import faiss
    import numpy as np
    import ollama
    
    index_path = index_dir / "index.faiss"
    metadata_path = index_dir / "metadata.json"
    
    if not index_path.exists():
        raise FileNotFoundError(f"Index not found at {index_path}")
    
    # Load index and metadata
    index = faiss.read_index(str(index_path))
    with open(metadata_path) as f:
        metadata = json.load(f)
    
    # Generate query embedding
    response = ollama.embeddings(
        model=settings.embedding_model,
        prompt=query
    )
    query_embedding = np.array([response["embedding"]]).astype('float32')
    faiss.normalize_L2(query_embedding)
    
    # Search
    distances, indices = index.search(query_embedding, k)
    
    results = []
    for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
        if idx < len(metadata):
            result = metadata[idx].copy()
            result["distance"] = float(dist)
            result["rank"] = i + 1
            result["citation"] = f"{result['pdf_name']}, Page {result['page_num']}"
            results.append(result)
    
    return results


def _chunk_text(text: str, max_tokens: int = 500, overlap: int = 50) -> List[str]:
    """
    Split text into overlapping chunks
    Simple word-based tokenization (approx 4 chars per token)
    """
    words = text.split()
    chunk_size = max_tokens  # words ≈ tokens for estimation
    overlap_size = overlap
    
    chunks = []
    start = 0
    
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start = end - overlap_size if end < len(words) else end
    
    return chunks
