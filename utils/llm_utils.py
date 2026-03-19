import voyageai
from groq import Groq
from config.settings import settings

client = voyageai.Client(api_key = settings.voyage_api_key)
llm_client = Groq(api_key = settings.groq_api_key)

def embed(text: list[str], model: str = "voyage-4"):
    result = client.embed(text, model = model, output_dimension = 2048)
    return result.embeddings

