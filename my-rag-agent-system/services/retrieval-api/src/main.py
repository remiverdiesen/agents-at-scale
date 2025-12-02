from flask import Flask, request, jsonify
import psycopg2
from pgvector.psycopg2 import register_vector
from openai import OpenAI
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

try:
    # Initialize OpenAI client pointing to local Ollama
    client = OpenAI(
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        api_key="ollama" # required but unused by Ollama
    )
    embedding_model_name = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
    logger.info(f"Ollama client initialized with model {embedding_model_name}")
    embedding_model = True
except Exception as e:
    logger.error(f"Failed to initialize Ollama client: {e}", exc_info=True)
    client = None
    embedding_model = None

def get_db_connection():
    db_host = os.getenv("PGVECTOR_HOST", "localhost")
    db_name = os.getenv("PGVECTOR_DB", "vectors")
    db_user = os.getenv("PGVECTOR_USER", "postgres")
    db_password = os.getenv("PGVECTOR_PASSWORD", "arkragpass123")
    
    conn = psycopg2.connect(
        host=db_host,
        database=db_name,
        user=db_user,
        password=db_password
    )
    register_vector(conn)
    return conn

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "embedding_model_loaded": embedding_model is not None})

@app.route('/retrieve_chunks', methods=['POST'])
def retrieve_chunks():
    if client is None:
        return jsonify({"error": "Ollama client not initialized."}), 500
    
    try:
        data = request.json
        query = data.get('query')
        top_k = data.get('top_k', 5)
        
        if not query:
            return jsonify({"error": "query parameter is required"}), 400
        
        response = client.embeddings.create(
            input=query,
            model=embedding_model_name
        )
        query_embedding = response.data[0].embedding
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT content, metadata, 
                   1 - (embedding <=> %s::vector) as similarity
            FROM documents
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """, (query_embedding, query_embedding, top_k))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "content": row[0],
                "metadata": row[1],
                "similarity": float(row[2])
            })
        
        cursor.close()
        conn.close()
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"Error retrieving chunks: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    logger.info("Starting RAG Retrieval REST API server on port 8000")
    app.run(host="0.0.0.0", port=8000)
