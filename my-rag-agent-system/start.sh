#!/bin/bash
set -e

echo "🚀 Starting RAG System with Docker Compose..."
docker-compose up -d

echo "⏳ Waiting for Ollama to be ready..."
until curl -s http://localhost:11434/api/tags > /dev/null; do
    sleep 2
    echo -n "."
done
echo ""

echo "📥 Pulling models (this may take a while)..."
echo "   - Pulling embedding model: nomic-embed-text"
docker-compose exec ollama ollama pull nomic-embed-text
echo "   - Pulling chat model: llama3"
docker-compose exec ollama ollama pull llama3

echo "✅ Models ready!"

echo "📝 Ingesting sample data..."
# We run ingestion inside the retrieval-service container for convenience as it has python/deps
# But we need to mount the ingest script or copy it. 
# Actually, let's just run it from host if python is available, OR use a temporary container.
# Let's use a temporary container using the retrieval-service image.
docker-compose run --rm --entrypoint python retrieval-service /app/ingestion/ingest.py || {
    echo "⚠️  Ingestion failed. Make sure you have built the image."
    echo "   Try: docker-compose build"
}

echo ""
echo "🎉 System is ready!"
echo "   - Retrieval API: http://localhost:8000"
echo "   - Ollama API: http://localhost:11434"
echo ""
echo "🤖 To run the agent:"
echo "   cd simple-agent"
echo "   pip install -r requirements.txt"
echo "   python agent.py"
