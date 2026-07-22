import sys
import requests
from qdrant_client import QdrantClient

# --- Config ---
QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "weaver_stable"

NOMIC_URL = "http://10.0.0.2:8081/v1/embeddings"
DEEPSEEK_URL = "http://10.0.0.2:8080/v1/chat/completions"
API_KEY = "TEST1234"

client = QdrantClient(url=QDRANT_URL)

def get_query_vector(text):
    response = client.models.embed_content(
        model="text-embedding-004",
        contents=text,
        config=dict(task_type="RETRIEVAL_QUERY")
    )
    return response.embeddings[0].values

def ask_gemini(query, context):
    # Using the latest 3.5-flash model for strict coding logic
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

def ask_deepseek(query, context):
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

    system_prompt = (
        "You are an expert C/Lua engine developer. "
        "Use the provided code context to answer the user's question accurately and concisely."
    )

    user_prompt = f"RETRIEVED CODE CONTEXT:\n{context}\n\nUSER QUESTION:\n{query}"

    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.2
    }

    res = requests.post(DEEPSEEK_URL, json=payload, headers=headers)
    res.raise_for_status()
    return res.json()["choices"][0]["message"]["content"]

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ask.py \"How does tenant mailbox synchronization work?\"")
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    print(f"🔍 Searching vector database for: '{query}'...")
    context = search_codebase(query)

    print("🤖 Thinking...")
    response = ask_deepseek(query, context)

    print("\n" + "="*50)
    print(response)
    print("="*50)
