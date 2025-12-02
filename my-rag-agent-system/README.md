# My RAG Agent System (Docker + Ollama)

This project implements a fully local, Docker-based RAG (Retrieval-Augmented Generation) system. It replaces cloud dependencies (Azure OpenAI) with **Ollama** and Kubernetes with **Docker Compose**.

## Architecture

- **Ollama**: Local LLM (Llama 3) and Embeddings (Nomic Embed Text).
- **pgvector**: PostgreSQL database for storing vector embeddings.
- **Retrieval Service**: Flask API that connects the Agent to the Database.
- **Agent**: A simple Python client that queries the system.

## Prerequisites

- Docker & Docker Compose
- Python 3.10+ (for running the agent client)

## Quick Start

1.  **Start the System**:
    Run the helper script to build containers, start services, pull models, and ingest data.
    ```bash
    ./start.sh
    ```

2.  **Run the Agent**:
    Open a new terminal and run the interactive agent.
    ```bash
    cd simple-agent
    pip install -r requirements.txt
    python agent.py
    ```

3.  **Chat**:
    Ask questions like:
    > "How do I create an agent in ARK?"
    > "What is an MCP server?"

## Manual Setup

If you prefer running commands manually:

1.  **Start Services**:
    ```bash
    docker-compose up -d --build
    ```

2.  **Pull Models**:
    ```bash
    docker-compose exec ollama ollama pull nomic-embed-text
    docker-compose exec ollama ollama pull llama3
    ```

3.  **Ingest Data**:
    We run the ingestion script inside the container network to access pgvector and ollama easily.
    ```bash
    # Copy ingest script to container (or mount it)
    docker cp ingestion/ingest.py $(docker-compose ps -q retrieval-service):/app/ingest.py
    
    # Run it
    docker-compose exec retrieval-service python /app/ingest.py
    ```

## Project Structure

- `docker-compose.yml`: Defines the services (DB, AI, API).
- `services/retrieval-api/`: The API that performs vector search.
- `ingestion/`: Script to load documents into the DB.
- `simple-agent/`: The client application that acts as the AI Agent.
- `init.sql`: Database schema initialization.
