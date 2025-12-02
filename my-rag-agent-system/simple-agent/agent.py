import requests
from openai import OpenAI
import os
import json

# Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
RETRIEVAL_SERVICE_URL = os.getenv("RETRIEVAL_SERVICE_URL", "http://localhost:8000/retrieve_chunks")
CHAT_MODEL = os.getenv("CHAT_MODEL", "llama3")

print(f"🤖 Initializing Agent...")
print(f"   Ollama URL: {OLLAMA_BASE_URL}")
print(f"   Retrieval URL: {RETRIEVAL_SERVICE_URL}")
print(f"   Model: {CHAT_MODEL}")

client = OpenAI(
    base_url=OLLAMA_BASE_URL,
    api_key="ollama"
)

def retrieve_context(query):
    """Call the retrieval service to get relevant chunks."""
    try:
        response = requests.post(
            RETRIEVAL_SERVICE_URL,
            json={"query": query, "top_k": 3}
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error retrieving context: {e}")
        return []

def chat_with_rag(user_query):
    """Main agent loop: Retrieve -> Augment -> Generate."""
    print(f"\n👤 User: {user_query}")
    
    # 1. Retrieve
    print("🔍 Agent: Searching knowledge base...")
    chunks = retrieve_context(user_query)
    
    if not chunks:
        print("⚠️  Agent: No relevant information found in knowledge base.")
        context_str = "No relevant context found."
    else:
        print(f"✅ Agent: Found {len(chunks)} relevant chunks.")
        context_str = "\n\n".join([f"--- Source ({c['similarity']:.2f}) ---\n{c['content']}" for c in chunks])

    # 2. Augment Prompt
    system_prompt = f"""You are a helpful AI assistant. 
Use the following context to answer the user's question. 
If the answer is not in the context, say you don't know.

Context:
{context_str}
"""

    # 3. Generate
    print("💭 Agent: Thinking...")
    try:
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query}
            ],
            stream=True
        )
        
        print("🤖 Agent: ", end="", flush=True)
        full_response = ""
        for chunk in response:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                print(content, end="", flush=True)
                full_response += content
        print("\n")
        
    except Exception as e:
        print(f"\n❌ Error generating response: {e}")

def main():
    print("\n✨ Agent Ready! Type 'exit' to quit.\n")
    while True:
        try:
            user_input = input(">> ")
            if user_input.lower() in ['exit', 'quit']:
                break
            if not user_input.strip():
                continue
                
            chat_with_rag(user_input)
            
        except KeyboardInterrupt:
            break
    print("\n👋 Goodbye!")

if __name__ == "__main__":
    main()
