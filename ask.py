import sys
import google.generativeai as genai
from qdrant_client import QdrantClient

# --- Config ---
QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "weaver_stable"

genai.configure(api_key="YOUR_GEMINI_API_KEY")
client = QdrantClient(url=QDRANT_URL)

def get_query_vector(text):
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=text,
        task_type="retrieval_query"
    )
    return result['embedding']

def search_codebase(query, limit=3):
    query_vector = get_query_vector(query)
    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=limit
    )

    contexts = []
    for point in results.points:
        payload = point.payload
        contexts.append(f"--- FILE: {payload['file']} (Chunk {payload['chunk_index']}) ---\n{payload['content']}")
    return "\n\n".join(contexts)

def ask_gemini(query, context):
    # We can pass the system prompt directly into the model initialization
    model = genai.GenerativeModel(
        model_name='gemini-1.5-pro',
        system_instruction="You are an expert C/Lua engine developer. Use the provided code context to answer the user's question accurately and concisely."
    )

    prompt = f"RETRIEVED CODE CONTEXT:\n{context}\n\nUSER QUESTION:\n{query}"

    # Generate the response with a low temperature for strict coding accuracy
    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(temperature=0.2)
    )
    return response.text

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ask.py \"How does tenant mailbox synchronization work?\"")
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    print(f"🔍 Searching vector database for: '{query}'...")
    context = search_codebase(query)

    print("🤖 Gemini is thinking...")
    response = ask_gemini(query, context)

    print("\n" + "="*50)
    print(response)
    print("="*50)
