import chromadb
import ollama
from typing import List

class VectorStore:
    def __init__(self, collection_name="secure_docs"):
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.collection_name = collection_name
        # Initial connection to the collection
        self.collection = self.client.get_or_create_collection(name=self.collection_name)

    def add_documents(self, texts: List[str], ids: List[str]):
        """Converts text chunks into embeddings and stores them."""
        for text, doc_id in zip(texts, ids):
            response = ollama.embeddings(model="nomic-embed-text", prompt=text)
            embedding = response["embedding"]
            self.collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[text]
            )

    def query(self, query_text: str, n_results=3) -> str:
        """Finds relevant chunks. Returns empty string if collection is missing/empty."""
        try:
            # Check if database is empty before querying
            if self.collection.count() == 0:
                return ""
                
            response = ollama.embeddings(model="nomic-embed-text", prompt=query_text)
            query_embedding = response["embedding"]
            
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )
            return "\n\n".join(results['documents'][0])
        except Exception as e:
            # If the collection ID is not found, return empty context instead of crashing
            print(f"Query handled error: {e}")
            return ""

    def clear_database(self):
        """Wipes the physical collection and resets the internal reference to prevent NotFoundErrors."""
        try:
            # Physically delete the collection from disk
            self.client.delete_collection(name=self.collection_name)
            
            # RE-INITIALIZE: This updates the pointer so the rest of the app doesn't look for a dead ID
            self.collection = self.client.get_or_create_collection(name=self.collection_name)
            return True
        except Exception as e:
            # If deletion fails (e.g. doesn't exist), just ensure we have a valid pointer now
            self.collection = self.client.get_or_create_collection(name=self.collection_name)
            print(f"Clear database handled error: {e}")
            return True