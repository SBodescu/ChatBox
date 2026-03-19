from groq import Groq
from config.settings import settings
from api.services.files_service import search_files_content_hybrid
from utils.llm_utils import llm_client
from sqlalchemy.orm import Session

def get_answer_from_db(query: str, user_id: int, db: Session):
    search_results = search_files_content_hybrid(query, user_id, db, 5)
    if not search_results:
        return "There are no results for this search"
    
    context_parts = []
    sources_for_response = []
    for res in search_results:
        source_name = res["file"]["original_name"]
        text = res["best_chunk"]
        context_parts.append(f"--- Sursa: {source_name} ---\n{text}")
        sources_for_response.append({
            "file_name": source_name,
            "file_id": res["file"]["id"],
            "relevance_score": res["score"],
            "text_snippet": text 
        })
    
    full_context = "\n\n".join(context_parts)

    system_prompt = (
        "You are a helpful AI assistant. Answer the user's question based ONLY on the provided context. "
        "If the answer is not in the context, say you don't know. Always cite the source file name."
    )

    completion = llm_client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n{full_context}\n\nÎntrebare: {query}"}
        ],
    )
    answer = completion.choices[0].message.content
    return answer, sources_for_response