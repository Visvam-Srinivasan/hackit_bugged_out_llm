import chromadb
import ollama
from typing import List

class VectorStore:
    def __init__(self, collection_name="secure_docs"):
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def add_documents(self, texts: List[str], ids: List[str]):
        # Generate embeddings using Ollama's local embedding model
        for text, doc_id in zip(texts, ids):
            response = ollama.embeddings(model="nomic-embed-text", prompt=text)
            embedding = response["embedding"]
            self.collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[text]
            )

    def query(self, query_text: str, n_results=3) -> str:
        # Embed the query
        response = ollama.embeddings(model="nomic-embed-text", prompt=query_text)
        query_embedding = response["embedding"]
        
        # Search the database
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        # Join retrieved documents into a single context string
        return "\n\n".join(results['documents'][0])