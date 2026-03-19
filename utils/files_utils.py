from pathlib import Path
from fastapi import File, UploadFile
import uuid
import re 
from config.settings import settings
from utils.llm_utils import embed

def generate_file_name(file_name: str):
    
    unique_id = uuid.uuid4().hex
    
    path_obj = Path(file_name)
    base_name = path_obj.stem
    extension = path_obj.suffix
    
    return f"{base_name}_{unique_id}{extension}"

def create_file_details(user_id: int,file: UploadFile = File(...)):
    safe_name = Path(file.filename).name
    generated_name = generate_file_name(safe_name)
    user_dir = Path(settings.UPLOAD_DIR)/ str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    dest = user_dir / generated_name

    return safe_name,generated_name,dest

def chunk_by_sentence(text: str, max_sentences_per_chunk: int = 3, overlap_sentences: int = 1):
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    chunks = []
    start_idx = 0 
    while start_idx < len(sentences):
        end_idx = min(start_idx + max_sentences_per_chunk, len(sentences))
        chunks.append(" ".join(sentences[start_idx:end_idx]))
        start_idx += max_sentences_per_chunk - overlap_sentences
        if start_idx < 0:
            start_idx = 0
    return chunks

def chunk_by_section(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"\n## ", text) if s.strip()]

def chunk_and_embed_by_file_type(text: str, content_type: str):
    if content_type == "text/markdown":
        chunks = chunk_by_section(text)
    else:
        chunks = chunk_by_sentence(text,3,1)
    
    if not chunks:
        return []
    
    embeddings = embed(chunks)
    results = []
    for chunk, embedded_chunk in zip(chunks,embeddings):
        results.append({
            "chunk_text": chunk,
            "embedding": embedded_chunk
        })
        
    return results
        

def rrf_ranking(embedding_results: list[dict], tsv_results: list[dict], k:int = 60):
    rrf_results = {}
    for rank, item in enumerate(embedding_results, start=1):
        file_id = item["file"]["id"]
        if file_id not in rrf_results:
            rrf_results[file_id] = {"score": 0.0, "file": item["file"],"best_chunk": item["best_chunk"], "min_rank": rank}
        
        rrf_results[file_id]["score"] += 1.0 / (k + rank)
    
    for rank, item in enumerate(tsv_results, start=1):
        file_id = item["file"]["id"]
        if file_id not in rrf_results:
            rrf_results[file_id] = {"score": 0.0, "file": item["file"],"best_chunk": item["best_chunk"], "min_rank": rank}
        else:
            if rank< rrf_results[file_id]["min_rank"]:
                rrf_results[file_id]["best_chunk"] = item["best_chunk"]
                rrf_results[file_id]["min_rank"] = rank
        
        rrf_results[file_id]["score"] += 1.0 / (k + rank)

    final_ranked = sorted(rrf_results.values(), key=lambda x: x["score"], reverse=True)
    for item in final_ranked:
        item.pop("min_rank", None)
    
    return final_ranked
