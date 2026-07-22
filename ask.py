import sys
from google import genai
from qdrant_client import QdrantClient

# --- Config ---
QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "weaver_stable"

# The SDK automatically checks os.environ["GEMINI_API_KEY"]
client = genai.Client()
qdrant = QdrantClient(url=QDRANT_URL)

def get_query_vector(text):
    response = client.models.embed_content(
        model="text-embedding-004",
        contents=text,
        config=dict(task_type="RETRIEVAL_QUERY")
    )
    return response.embeddings[0].values

def search_codebase(query, limit=3):
    query_vector = get_query_vector(query)
    results = qdrant.query_points(
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
    prompt = f"RETRIEVED CODE CONTEXT:\n{context}\n\nUSER QUESTION:\n{query}"

    response = client.models.generate_content(
        model='gemini-3.5-flash',
        contents=prompt,
        config=dict(
            system_instruction="You are an expert C/Lua engine developer. Use the provided code context to answer the user's question accurately and concisely.",
            temperature=0.2
        )
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
