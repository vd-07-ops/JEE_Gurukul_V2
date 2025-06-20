from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from typing import List, Dict, Any, Tuple
import pickle
import io
from cloud_config import cloud_storage, STORAGE_PATHS

class RAGEngine:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.documents = []
        self.vector_dimension = 384  # Dimension for all-MiniLM-L6-v2
        
    def _create_index(self):
        """Create a new FAISS index."""
        self.index = faiss.IndexFlatL2(self.vector_dimension)
        
    def _process_mmd_content(self, content: str) -> List[str]:
        """Split MMD content into chunks for processing."""
        # Split by double newlines to get meaningful chunks
        chunks = [chunk.strip() for chunk in content.split('\n\n') if chunk.strip()]
        return chunks
    
    def build_vector_db(self, subject: str):
        """Build vector database from MMD file for a specific subject."""
        # Get MMD content
        mmd_content = cloud_storage.get_mmd_content(subject)
        if not mmd_content:
            raise ValueError(f"No MMD content found for subject: {subject}")
            
        # Process content into chunks
        chunks = self._process_mmd_content(mmd_content)
        self.documents = chunks
        
        # Create embeddings
        embeddings = self.model.encode(chunks)
        
        # Create and populate FAISS index
        self._create_index()
        self.index.add(np.array(embeddings).astype('float32'))
        
        # Save to cloud storage
        self._save_to_cloud(subject)
        
    def _save_to_cloud(self, subject: str):
        """Save the vector database to Google Cloud Storage."""
        # Save FAISS index
        index_bytes = faiss.serialize_index(self.index)
        index_blob_name = f'vector_db/{subject}_index.faiss'
        cloud_storage.upload_file_from_memory(index_bytes, index_blob_name)
        
        # Save documents
        documents_blob_name = f'vector_db/{subject}_documents.pkl'
        documents_bytes = pickle.dumps(self.documents)
        cloud_storage.upload_file_from_memory(documents_bytes, documents_blob_name)
        
    def load_from_cloud(self, subject: str):
        """Load vector database from Google Cloud Storage."""
        # Load FAISS index
        index_blob_name = f'vector_db/{subject}_index.faiss'
        index_bytes = cloud_storage.get_binary_file(index_blob_name)
        self.index = faiss.deserialize_index(index_bytes)
        
        # Load documents
        documents_blob_name = f'vector_db/{subject}_documents.pkl'
        documents_bytes = cloud_storage.get_binary_file(documents_blob_name)
        self.documents = pickle.loads(documents_bytes)
        
    def search(self, query: str, k: int = 3) -> List[Tuple[str, float]]:
        """Search for relevant content using the query."""
        if not self.index:
            raise ValueError("Vector database not loaded. Call load_from_cloud first.")
            
        # Create query embedding
        query_embedding = self.model.encode([query])
        
        # Search in FAISS index
        distances, indices = self.index.search(
            np.array(query_embedding).astype('float32'), k
        )
        
        # Return results with their distances
        results = []
        for idx, distance in zip(indices[0], distances[0]):
            if idx < len(self.documents):
                results.append((self.documents[idx], float(distance)))
                
        return results

# Initialize RAG engine
rag_engine = RAGEngine() 