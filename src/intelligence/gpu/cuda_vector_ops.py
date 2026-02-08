"""
CUDA-Accelerated Vector Operations

Provides GPU-accelerated similarity search and embedding operations
using FAISS-GPU, CuPy, or PyTorch CUDA tensors.

Features:
- Batch cosine similarity on GPU
- Approximate nearest neighbor search
- Large-scale vector indexing
- Memory-efficient batch processing

Requirements:
- NVIDIA GPU with CUDA
- faiss-gpu (optional, recommended)
- cupy (optional)
- torch with CUDA (fallback)
"""

from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass
import math
import json
from pathlib import Path

# Try imports in order of preference
try:
    import torch
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None
    F = None

try:
    import faiss
    FAISS_AVAILABLE = True
    # Check for GPU support
    FAISS_GPU_AVAILABLE = hasattr(faiss, 'StandardGpuResources')
except ImportError:
    FAISS_AVAILABLE = False
    FAISS_GPU_AVAILABLE = False
    faiss = None

try:
    import cupy as cp
    CUPY_AVAILABLE = True
except ImportError:
    CUPY_AVAILABLE = False
    cp = None

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

from .device_manager import get_device, get_device_manager


@dataclass
class SimilarityResult:
    """Result of a similarity search."""
    ids: List[str]
    scores: List[float]
    documents: List[str]
    metadata: List[Dict[str, Any]]


class CUDAVectorOps:
    """
    GPU-accelerated vector operations.
    
    Provides fast similarity computation using the best available backend:
    1. FAISS-GPU (fastest for large datasets)
    2. CuPy (good for medium datasets)
    3. PyTorch CUDA (fallback)
    4. NumPy (CPU fallback)
    """
    
    def __init__(self, force_cpu: bool = False):
        self._device_manager = get_device_manager()
        self._force_cpu = force_cpu
        self._device = "cpu" if force_cpu else self._device_manager.device
        
        # Select backend
        self._backend = self._select_backend()
        print(f"🔧 Vector ops backend: {self._backend} on {self._device}")
    
    def _select_backend(self) -> str:
        """Select the best available backend."""
        if self._force_cpu:
            return "numpy"
        
        if self._device == "cuda":
            if FAISS_GPU_AVAILABLE:
                return "faiss_gpu"
            elif CUPY_AVAILABLE:
                return "cupy"
            elif TORCH_AVAILABLE:
                return "torch_cuda"
        
        if FAISS_AVAILABLE:
            return "faiss_cpu"
        
        return "numpy"
    
    def cosine_similarity_batch(
        self,
        queries: List[List[float]],
        vectors: List[List[float]]
    ) -> List[List[float]]:
        """
        Compute cosine similarity between query vectors and a set of vectors.
        
        Args:
            queries: List of query vectors [num_queries, dim]
            vectors: List of vectors to compare against [num_vectors, dim]
            
        Returns:
            Similarity matrix [num_queries, num_vectors]
        """
        if self._backend == "torch_cuda" or self._backend.startswith("torch"):
            return self._cosine_torch(queries, vectors)
        elif self._backend == "cupy":
            return self._cosine_cupy(queries, vectors)
        else:
            return self._cosine_numpy(queries, vectors)
    
    def _cosine_torch(
        self, 
        queries: List[List[float]], 
        vectors: List[List[float]]
    ) -> List[List[float]]:
        """PyTorch CUDA cosine similarity."""
        device = self._device if TORCH_AVAILABLE and torch.cuda.is_available() else "cpu"
        
        q = torch.tensor(queries, dtype=torch.float32, device=device)
        v = torch.tensor(vectors, dtype=torch.float32, device=device)
        
        # Normalize
        q_norm = F.normalize(q, p=2, dim=1)
        v_norm = F.normalize(v, p=2, dim=1)
        
        # Compute similarity
        similarity = torch.mm(q_norm, v_norm.t())
        
        return similarity.cpu().tolist()
    
    def _cosine_cupy(
        self, 
        queries: List[List[float]], 
        vectors: List[List[float]]
    ) -> List[List[float]]:
        """CuPy GPU cosine similarity."""
        q = cp.array(queries, dtype=cp.float32)
        v = cp.array(vectors, dtype=cp.float32)
        
        # Normalize
        q_norm = q / cp.linalg.norm(q, axis=1, keepdims=True)
        v_norm = v / cp.linalg.norm(v, axis=1, keepdims=True)
        
        # Compute similarity
        similarity = cp.dot(q_norm, v_norm.T)
        
        return cp.asnumpy(similarity).tolist()
    
    def _cosine_numpy(
        self, 
        queries: List[List[float]], 
        vectors: List[List[float]]
    ) -> List[List[float]]:
        """NumPy CPU cosine similarity."""
        q = np.array(queries, dtype=np.float32)
        v = np.array(vectors, dtype=np.float32)
        
        # Normalize
        q_norm = q / (np.linalg.norm(q, axis=1, keepdims=True) + 1e-8)
        v_norm = v / (np.linalg.norm(v, axis=1, keepdims=True) + 1e-8)
        
        # Compute similarity
        similarity = np.dot(q_norm, v_norm.T)
        
        return similarity.tolist()
    
    def top_k_similar(
        self,
        query: List[float],
        vectors: List[List[float]],
        k: int = 5
    ) -> Tuple[List[int], List[float]]:
        """
        Find top-k most similar vectors.
        
        Args:
            query: Query vector
            vectors: Vector database
            k: Number of results
            
        Returns:
            Tuple of (indices, scores)
        """
        similarities = self.cosine_similarity_batch([query], vectors)[0]
        
        # Get top-k
        if NUMPY_AVAILABLE:
            sims = np.array(similarities)
            indices = np.argsort(sims)[::-1][:k]
            scores = sims[indices].tolist()
            return indices.tolist(), scores
        else:
            # Python fallback
            indexed = list(enumerate(similarities))
            indexed.sort(key=lambda x: x[1], reverse=True)
            indices = [i for i, _ in indexed[:k]]
            scores = [s for _, s in indexed[:k]]
            return indices, scores
    
    def get_backend_info(self) -> Dict[str, Any]:
        """Get information about the active backend."""
        return {
            "backend": self._backend,
            "device": self._device,
            "faiss_available": FAISS_AVAILABLE,
            "faiss_gpu_available": FAISS_GPU_AVAILABLE,
            "cupy_available": CUPY_AVAILABLE,
            "torch_available": TORCH_AVAILABLE,
            "numpy_available": NUMPY_AVAILABLE
        }


class GPUVectorStore:
    """
    GPU-accelerated vector store for embedding search.
    
    Features:
    - FAISS-GPU index for large-scale similarity search
    - Automatic GPU memory management
    - Hybrid CPU/GPU operation
    - Persistence support
    
    Usage:
        store = GPUVectorStore(dimension=768)
        store.add(ids, embeddings, documents, metadata)
        results = store.search(query_embedding, k=10)
    """
    
    def __init__(
        self,
        dimension: int = 768,
        index_type: str = "flat",  # "flat", "ivf", "hnsw"
        nlist: int = 100,  # Number of clusters for IVF
        persist_path: Optional[str] = None,
        force_cpu: bool = False
    ):
        self.dimension = dimension
        self.index_type = index_type
        self.nlist = nlist
        self.persist_path = Path(persist_path) if persist_path else None
        
        self._device_manager = get_device_manager()
        self._use_gpu = not force_cpu and self._device_manager.is_cuda_available
        
        # Storage
        self._ids: List[str] = []
        self._documents: List[str] = []
        self._metadata: List[Dict[str, Any]] = []
        
        # FAISS index
        self._index = None
        self._gpu_resources = None
        
        # Fallback ops
        self._vector_ops = CUDAVectorOps(force_cpu=force_cpu)
        self._raw_vectors: List[List[float]] = []  # Fallback storage
        
        self._initialize_index()
    
    def _initialize_index(self):
        """Initialize FAISS index."""
        if not FAISS_AVAILABLE:
            print("⚠️ FAISS not available, using fallback vector operations")
            return
        
        # Create CPU index first
        if self.index_type == "flat":
            self._index = faiss.IndexFlatIP(self.dimension)  # Inner product (cosine with normalized vectors)
        elif self.index_type == "ivf":
            quantizer = faiss.IndexFlatIP(self.dimension)
            self._index = faiss.IndexIVFFlat(quantizer, self.dimension, self.nlist)
        elif self.index_type == "hnsw":
            self._index = faiss.IndexHNSWFlat(self.dimension, 32)  # 32 = M parameter
        else:
            self._index = faiss.IndexFlatIP(self.dimension)
        
        # Move to GPU if available
        if self._use_gpu and FAISS_GPU_AVAILABLE:
            try:
                self._gpu_resources = faiss.StandardGpuResources()
                self._index = faiss.index_cpu_to_gpu(
                    self._gpu_resources, 
                    0,  # GPU device ID
                    self._index
                )
                print(f"🚀 FAISS index on GPU ({self.index_type})")
            except Exception as e:
                print(f"⚠️ Failed to move FAISS index to GPU: {e}")
                self._use_gpu = False
        else:
            print(f"📊 FAISS index on CPU ({self.index_type})")
        
        # Load persisted data if exists
        if self.persist_path and self.persist_path.exists():
            self._load()
    
    def add(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadata: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Add documents to the vector store.
        
        Args:
            ids: Document IDs
            embeddings: Vector embeddings
            documents: Document texts
            metadata: Optional metadata
        """
        if len(ids) != len(embeddings) or len(ids) != len(documents):
            raise ValueError("ids, embeddings, and documents must have same length")
        
        metadata = metadata or [{} for _ in ids]
        
        # Store metadata
        self._ids.extend(ids)
        self._documents.extend(documents)
        self._metadata.extend(metadata)
        
        # Normalize embeddings for cosine similarity
        if NUMPY_AVAILABLE:
            vectors = np.array(embeddings, dtype=np.float32)
            norms = np.linalg.norm(vectors, axis=1, keepdims=True)
            vectors = vectors / (norms + 1e-8)
        else:
            # Manual normalization
            vectors = []
            for emb in embeddings:
                norm = math.sqrt(sum(x * x for x in emb))
                vectors.append([x / (norm + 1e-8) for x in emb])
            vectors = vectors
        
        # Add to FAISS index
        if self._index is not None:
            if NUMPY_AVAILABLE:
                self._index.add(vectors)
            else:
                self._index.add(np.array(vectors, dtype=np.float32))
        else:
            # Fallback: store raw vectors
            self._raw_vectors.extend(embeddings)
        
        # Persist
        if self.persist_path:
            self._save()
    
    def search(
        self,
        query_embedding: List[float],
        k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> SimilarityResult:
        """
        Search for similar documents.
        
        Args:
            query_embedding: Query vector
            k: Number of results
            filter_metadata: Optional metadata filter
            
        Returns:
            SimilarityResult with matches
        """
        if len(self._ids) == 0:
            return SimilarityResult([], [], [], [])
        
        # Normalize query
        if NUMPY_AVAILABLE:
            query = np.array([query_embedding], dtype=np.float32)
            norm = np.linalg.norm(query)
            query = query / (norm + 1e-8)
        else:
            norm = math.sqrt(sum(x * x for x in query_embedding))
            query = [[x / (norm + 1e-8) for x in query_embedding]]
        
        # Search
        if self._index is not None:
            scores, indices = self._index.search(
                query if NUMPY_AVAILABLE else np.array(query, dtype=np.float32), 
                min(k * 2, len(self._ids))  # Fetch extra for filtering
            )
            scores = scores[0].tolist()
            indices = indices[0].tolist()
        else:
            # Fallback search
            indices, scores = self._vector_ops.top_k_similar(
                query_embedding,
                self._raw_vectors,
                k=min(k * 2, len(self._ids))
            )
        
        # Apply metadata filter and collect results
        result_ids = []
        result_scores = []
        result_docs = []
        result_meta = []
        
        for idx, score in zip(indices, scores):
            if idx < 0 or idx >= len(self._ids):
                continue
            
            # Check filter
            if filter_metadata:
                meta = self._metadata[idx]
                match = all(meta.get(k) == v for k, v in filter_metadata.items())
                if not match:
                    continue
            
            result_ids.append(self._ids[idx])
            result_scores.append(float(score))
            result_docs.append(self._documents[idx])
            result_meta.append(self._metadata[idx])
            
            if len(result_ids) >= k:
                break
        
        return SimilarityResult(
            ids=result_ids,
            scores=result_scores,
            documents=result_docs,
            metadata=result_meta
        )
    
    def delete(self, ids: List[str]):
        """Delete documents by ID (requires index rebuild)."""
        # Find indices to keep
        keep_indices = [i for i, id_ in enumerate(self._ids) if id_ not in ids]
        
        # Filter all storage
        self._ids = [self._ids[i] for i in keep_indices]
        self._documents = [self._documents[i] for i in keep_indices]
        self._metadata = [self._metadata[i] for i in keep_indices]
        
        if self._raw_vectors:
            self._raw_vectors = [self._raw_vectors[i] for i in keep_indices]
        
        # Rebuild index if using FAISS
        if self._index is not None and self._raw_vectors:
            self._initialize_index()
            if NUMPY_AVAILABLE:
                vectors = np.array(self._raw_vectors, dtype=np.float32)
                norms = np.linalg.norm(vectors, axis=1, keepdims=True)
                vectors = vectors / (norms + 1e-8)
                self._index.add(vectors)
        
        if self.persist_path:
            self._save()
    
    def count(self) -> int:
        """Return number of documents."""
        return len(self._ids)
    
    def _save(self):
        """Persist to disk."""
        if not self.persist_path:
            return
        
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "ids": self._ids,
            "documents": self._documents,
            "metadata": self._metadata,
            "raw_vectors": self._raw_vectors
        }
        
        with open(self.persist_path, 'w') as f:
            json.dump(data, f)
    
    def _load(self):
        """Load from disk."""
        if not self.persist_path or not self.persist_path.exists():
            return
        
        try:
            with open(self.persist_path, 'r') as f:
                data = json.load(f)
            
            self._ids = data.get("ids", [])
            self._documents = data.get("documents", [])
            self._metadata = data.get("metadata", [])
            self._raw_vectors = data.get("raw_vectors", [])
            
            # Rebuild FAISS index
            if self._index is not None and self._raw_vectors:
                if NUMPY_AVAILABLE:
                    vectors = np.array(self._raw_vectors, dtype=np.float32)
                    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
                    vectors = vectors / (norms + 1e-8)
                    self._index.add(vectors)
        except Exception as e:
            print(f"⚠️ Failed to load vector store: {e}")
    
    def get_info(self) -> Dict[str, Any]:
        """Get vector store information."""
        return {
            "count": len(self._ids),
            "dimension": self.dimension,
            "index_type": self.index_type,
            "using_gpu": self._use_gpu,
            "using_faiss": self._index is not None,
            "backend": self._vector_ops._backend
        }


def create_gpu_vector_store(
    dimension: int = 768,
    persist_path: Optional[str] = None
) -> GPUVectorStore:
    """
    Factory function to create optimally configured GPU vector store.
    
    Args:
        dimension: Embedding dimension
        persist_path: Optional persistence path
        
    Returns:
        Configured GPUVectorStore
    """
    # Auto-select index type based on expected size
    # (Could be made smarter based on available GPU memory)
    return GPUVectorStore(
        dimension=dimension,
        index_type="flat",  # Most accurate, fast for < 1M vectors
        persist_path=persist_path
    )
