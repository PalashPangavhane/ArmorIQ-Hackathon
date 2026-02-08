"""
GPU Acceleration Module

Provides NVIDIA CUDA acceleration for:
- GNN-based risk models (PyTorch + CUDA)
- Vector similarity search (FAISS-GPU or CuPy)
- Batch embedding operations

Requirements:
- NVIDIA GPU with CUDA capability
- PyTorch with CUDA support
- Optional: FAISS-GPU, CuPy
"""

from .device_manager import GPUDeviceManager, get_device, get_device_info
from .cuda_gnn import CUDAGraphNeuralNetwork, CUDAGNNRiskModel
from .cuda_vector_ops import CUDAVectorOps, GPUVectorStore

__all__ = [
    "GPUDeviceManager",
    "get_device",
    "get_device_info",
    "CUDAGraphNeuralNetwork",
    "CUDAGNNRiskModel",
    "CUDAVectorOps",
    "GPUVectorStore",
]
