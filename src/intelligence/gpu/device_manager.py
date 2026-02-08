"""
GPU Device Manager

Handles NVIDIA CUDA device detection, selection, and memory management.
Provides automatic fallback to CPU when GPU is unavailable.
"""

import os
import sys
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

# Try to import PyTorch with CUDA
try:
    import torch
    import torch.cuda as cuda
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None
    cuda = None

# Try to import CuPy for array operations
try:
    import cupy as cp
    CUPY_AVAILABLE = True
except ImportError:
    CUPY_AVAILABLE = False
    cp = None


class ComputeDevice(Enum):
    """Available compute devices."""
    CPU = "cpu"
    CUDA = "cuda"
    MPS = "mps"  # Apple Silicon


@dataclass
class GPUInfo:
    """Information about a GPU device."""
    device_id: int
    name: str
    total_memory_gb: float
    free_memory_gb: float
    compute_capability: Tuple[int, int]
    is_available: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "name": self.name,
            "total_memory_gb": round(self.total_memory_gb, 2),
            "free_memory_gb": round(self.free_memory_gb, 2),
            "compute_capability": f"{self.compute_capability[0]}.{self.compute_capability[1]}",
            "is_available": self.is_available
        }


class GPUDeviceManager:
    """
    Manages GPU device selection and memory for CUDA acceleration.
    
    Features:
    - Automatic device detection
    - Memory monitoring
    - Multi-GPU support
    - Graceful CPU fallback
    
    Usage:
        manager = GPUDeviceManager()
        device = manager.get_optimal_device()
        tensor = tensor.to(device)
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern for global device management."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._device: Optional[str] = None
        self._gpu_info: Optional[GPUInfo] = None
        self._force_cpu = os.environ.get("ARMORIQ_FORCE_CPU", "0") == "1"
        self._initialized = True
        
        # Initialize device
        self._detect_devices()
    
    def _detect_devices(self):
        """Detect available compute devices."""
        if self._force_cpu:
            self._device = "cpu"
            print("⚙️ GPU disabled by ARMORIQ_FORCE_CPU environment variable")
            return
        
        if not TORCH_AVAILABLE:
            self._device = "cpu"
            print("⚠️ PyTorch not installed. Install with: pip install torch --index-url https://download.pytorch.org/whl/cu121")
            return
        
        # Check for CUDA
        if torch.cuda.is_available():
            self._device = "cuda"
            self._gpu_info = self._get_gpu_info(0)
            print(f"🚀 CUDA GPU detected: {self._gpu_info.name}")
            print(f"   Memory: {self._gpu_info.free_memory_gb:.1f}GB free / {self._gpu_info.total_memory_gb:.1f}GB total")
            print(f"   Compute Capability: {self._gpu_info.compute_capability[0]}.{self._gpu_info.compute_capability[1]}")
        # Check for Apple Silicon MPS
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            self._device = "mps"
            print("🍎 Apple Silicon MPS detected")
        else:
            self._device = "cpu"
            print("⚠️ No GPU detected, using CPU")
    
    def _get_gpu_info(self, device_id: int = 0) -> GPUInfo:
        """Get detailed GPU information."""
        if not TORCH_AVAILABLE or not torch.cuda.is_available():
            return GPUInfo(
                device_id=-1,
                name="No GPU",
                total_memory_gb=0,
                free_memory_gb=0,
                compute_capability=(0, 0),
                is_available=False
            )
        
        props = torch.cuda.get_device_properties(device_id)
        total_mem = props.total_memory / (1024**3)
        free_mem = (props.total_memory - torch.cuda.memory_allocated(device_id)) / (1024**3)
        
        return GPUInfo(
            device_id=device_id,
            name=props.name,
            total_memory_gb=total_mem,
            free_memory_gb=free_mem,
            compute_capability=(props.major, props.minor),
            is_available=True
        )
    
    @property
    def device(self) -> str:
        """Get current device string."""
        return self._device
    
    @property
    def is_cuda_available(self) -> bool:
        """Check if CUDA is available."""
        return self._device == "cuda"
    
    @property
    def is_gpu_available(self) -> bool:
        """Check if any GPU (CUDA or MPS) is available."""
        return self._device in ("cuda", "mps")
    
    def get_torch_device(self) -> "torch.device":
        """Get PyTorch device object."""
        if not TORCH_AVAILABLE:
            raise RuntimeError("PyTorch not installed")
        return torch.device(self._device)
    
    def get_optimal_device(self, min_memory_gb: float = 2.0) -> str:
        """
        Get optimal device based on available memory.
        
        Args:
            min_memory_gb: Minimum required GPU memory in GB
            
        Returns:
            Device string ('cuda', 'mps', or 'cpu')
        """
        if self._device == "cuda" and self._gpu_info:
            if self._gpu_info.free_memory_gb >= min_memory_gb:
                return "cuda"
            else:
                print(f"⚠️ Insufficient GPU memory ({self._gpu_info.free_memory_gb:.1f}GB < {min_memory_gb}GB), using CPU")
                return "cpu"
        return self._device
    
    def get_all_gpus(self) -> list[GPUInfo]:
        """Get info for all available GPUs."""
        if not TORCH_AVAILABLE or not torch.cuda.is_available():
            return []
        
        num_gpus = torch.cuda.device_count()
        return [self._get_gpu_info(i) for i in range(num_gpus)]
    
    def set_device(self, device_id: int = 0):
        """Set the active CUDA device."""
        if TORCH_AVAILABLE and torch.cuda.is_available():
            torch.cuda.set_device(device_id)
            self._gpu_info = self._get_gpu_info(device_id)
    
    def clear_cache(self):
        """Clear GPU memory cache."""
        if TORCH_AVAILABLE and torch.cuda.is_available():
            torch.cuda.empty_cache()
            print("🧹 GPU memory cache cleared")
    
    def get_memory_stats(self) -> Dict[str, float]:
        """Get current GPU memory statistics."""
        if not TORCH_AVAILABLE or not torch.cuda.is_available():
            return {"error": "CUDA not available"}
        
        allocated = torch.cuda.memory_allocated() / (1024**3)
        reserved = torch.cuda.memory_reserved() / (1024**3)
        total = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        
        return {
            "allocated_gb": round(allocated, 3),
            "reserved_gb": round(reserved, 3),
            "total_gb": round(total, 3),
            "free_gb": round(total - allocated, 3)
        }
    
    def synchronize(self):
        """Synchronize CUDA operations."""
        if TORCH_AVAILABLE and torch.cuda.is_available():
            torch.cuda.synchronize()


# Global singleton accessors
_device_manager: Optional[GPUDeviceManager] = None


def get_device_manager() -> GPUDeviceManager:
    """Get the global GPU device manager."""
    global _device_manager
    if _device_manager is None:
        _device_manager = GPUDeviceManager()
    return _device_manager


def get_device() -> str:
    """Get the current compute device string."""
    return get_device_manager().device


def get_device_info() -> Dict[str, Any]:
    """Get device information as dictionary."""
    manager = get_device_manager()
    
    info = {
        "device": manager.device,
        "is_gpu_available": manager.is_gpu_available,
        "is_cuda_available": manager.is_cuda_available,
        "torch_available": TORCH_AVAILABLE,
        "cupy_available": CUPY_AVAILABLE,
    }
    
    if manager._gpu_info:
        info["gpu"] = manager._gpu_info.to_dict()
    
    if manager.is_cuda_available:
        info["memory"] = manager.get_memory_stats()
    
    return info


def to_device(tensor_or_model, device: Optional[str] = None):
    """
    Move tensor or model to device.
    
    Args:
        tensor_or_model: PyTorch tensor or model
        device: Target device (None = auto-detect)
        
    Returns:
        Tensor or model on target device
    """
    if not TORCH_AVAILABLE:
        return tensor_or_model
    
    if device is None:
        device = get_device()
    
    return tensor_or_model.to(device)
