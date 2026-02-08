"""
GPU Acceleration Test Suite

Tests NVIDIA CUDA acceleration for ArmorIQ components:
1. Device detection
2. GNN risk model inference
3. Vector similarity search
4. Batch processing performance
"""

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_device_detection():
    """Test GPU device detection."""
    print("\n" + "="*60)
    print("TEST 1: GPU Device Detection")
    print("="*60)
    
    from src.intelligence.gpu.device_manager import (
        GPUDeviceManager, 
        get_device, 
        get_device_info,
        TORCH_AVAILABLE,
        CUPY_AVAILABLE
    )
    
    print(f"\nPyTorch available: {TORCH_AVAILABLE}")
    print(f"CuPy available: {CUPY_AVAILABLE}")
    
    manager = GPUDeviceManager()
    print(f"\nDevice: {manager.device}")
    print(f"CUDA available: {manager.is_cuda_available}")
    print(f"GPU available: {manager.is_gpu_available}")
    
    if manager.is_cuda_available:
        print(f"\nGPU Info:")
        for gpu in manager.get_all_gpus():
            print(f"  - {gpu.name}")
            print(f"    Memory: {gpu.free_memory_gb:.1f}GB free / {gpu.total_memory_gb:.1f}GB total")
            print(f"    Compute: {gpu.compute_capability}")
        
        print(f"\nMemory Stats: {manager.get_memory_stats()}")
    
    info = get_device_info()
    print(f"\nDevice Info: {info}")
    
    return manager.device != "cpu"


def test_gnn_risk_model():
    """Test GPU-accelerated GNN risk model."""
    print("\n" + "="*60)
    print("TEST 2: CUDA GNN Risk Model")
    print("="*60)
    
    try:
        from src.intelligence.gpu.cuda_gnn import CUDAGNNRiskModel, TORCH_AVAILABLE, TORCH_GEOMETRIC_AVAILABLE
        
        print(f"\nPyTorch available: {TORCH_AVAILABLE}")
        print(f"PyTorch Geometric available: {TORCH_GEOMETRIC_AVAILABLE}")
        
        if not TORCH_AVAILABLE:
            print("⚠️ PyTorch not installed - skipping neural test")
            return False
        
        # Create model
        model = CUDAGNNRiskModel()
        print(f"\nInitializing model...")
        model.initialize()
        
        print(f"Device info: {model.get_device_info()}")
        
        # Test transaction
        test_transaction = {
            "amount": 15000,
            "vendor": "Unknown Vendor Inc",
            "category": "consulting",
            "employee_id": "emp_001",
            "timestamp": "2026-02-08T14:30:00"
        }
        
        print(f"\nTest transaction: ${test_transaction['amount']} to {test_transaction['vendor']}")
        
        # Predict
        start = time.perf_counter()
        result = model.predict_risk(test_transaction)
        elapsed = (time.perf_counter() - start) * 1000
        
        print(f"\nRisk Score: {result['risk_score']:.3f}")
        print(f"Risk Level: {result['risk_level']}")
        print(f"Risk Reasons: {result.get('risk_reasons', [])}")
        print(f"Inference Mode: {result.get('inference_mode', 'unknown')}")
        print(f"Inference Time: {elapsed:.2f}ms")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_batch_inference():
    """Test batch inference performance."""
    print("\n" + "="*60)
    print("TEST 3: Batch Inference Performance")
    print("="*60)
    
    try:
        from src.intelligence.gpu.cuda_gnn import CUDAGNNRiskModel, TORCH_AVAILABLE
        
        if not TORCH_AVAILABLE:
            print("⚠️ PyTorch not installed - skipping batch test")
            return False
        
        model = CUDAGNNRiskModel()
        model.initialize()
        
        # Generate test batch
        batch_sizes = [10, 100, 500]
        
        for batch_size in batch_sizes:
            transactions = [
                {
                    "amount": 1000 + i * 100,
                    "vendor": f"Vendor_{i % 50}",
                    "category": ["office", "travel", "consulting"][i % 3],
                    "employee_id": f"emp_{i % 20}",
                    "timestamp": "2026-02-08T14:30:00"
                }
                for i in range(batch_size)
            ]
            
            # Batch prediction
            start = time.perf_counter()
            results = model.predict_batch(transactions)
            elapsed = (time.perf_counter() - start) * 1000
            
            print(f"\nBatch size: {batch_size}")
            print(f"  Total time: {elapsed:.1f}ms")
            print(f"  Per transaction: {elapsed/batch_size:.3f}ms")
            print(f"  Throughput: {batch_size/(elapsed/1000):.0f} transactions/sec")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


def test_vector_operations():
    """Test GPU-accelerated vector operations."""
    print("\n" + "="*60)
    print("TEST 4: GPU Vector Operations")
    print("="*60)
    
    try:
        from src.intelligence.gpu.cuda_vector_ops import CUDAVectorOps, GPUVectorStore
        import random
        
        # Test vector ops
        ops = CUDAVectorOps()
        print(f"\nBackend: {ops._backend}")
        print(f"Backend info: {ops.get_backend_info()}")
        
        # Generate test vectors
        dim = 768
        num_vectors = 1000
        num_queries = 10
        
        print(f"\nGenerating {num_vectors} vectors of dimension {dim}...")
        vectors = [[random.gauss(0, 1) for _ in range(dim)] for _ in range(num_vectors)]
        queries = [[random.gauss(0, 1) for _ in range(dim)] for _ in range(num_queries)]
        
        # Benchmark similarity
        print(f"Computing similarity for {num_queries} queries...")
        start = time.perf_counter()
        similarities = ops.cosine_similarity_batch(queries, vectors)
        elapsed = (time.perf_counter() - start) * 1000
        
        print(f"  Time: {elapsed:.2f}ms")
        print(f"  Similarity matrix shape: {len(similarities)} x {len(similarities[0])}")
        
        # Test vector store
        print(f"\nTesting GPU Vector Store...")
        store = GPUVectorStore(dimension=dim, index_type="flat")
        print(f"Store info: {store.get_info()}")
        
        # Add vectors
        ids = [f"doc_{i}" for i in range(num_vectors)]
        docs = [f"Document {i}" for i in range(num_vectors)]
        
        start = time.perf_counter()
        store.add(ids, vectors, docs)
        add_elapsed = (time.perf_counter() - start) * 1000
        print(f"  Add {num_vectors} vectors: {add_elapsed:.2f}ms")
        
        # Search
        start = time.perf_counter()
        results = store.search(queries[0], k=10)
        search_elapsed = (time.perf_counter() - start) * 1000
        print(f"  Search time: {search_elapsed:.2f}ms")
        print(f"  Top result: {results.ids[0]} (score: {results.scores[0]:.3f})")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_risk_service_integration():
    """Test GPU integration with risk assessment service."""
    print("\n" + "="*60)
    print("TEST 5: Risk Service GPU Integration")
    print("="*60)
    
    try:
        from src.intelligence.gnn.risk_service import RiskAssessmentService
        
        # Create service with GPU
        print("\nCreating risk service with GPU acceleration...")
        service = RiskAssessmentService(use_gpu=True)
        
        print(f"Device info: {service.get_device_info()}")
        
        # Test single assessment
        transaction = {
            "amount": 25000,
            "vendor": "Suspicious Corp",
            "category": "services",
            "employee_id": "emp_test_001",
            "timestamp": "2026-02-08T23:45:00"  # Late night
        }
        
        print(f"\nAssessing transaction: ${transaction['amount']}")
        start = time.perf_counter()
        signal = service.assess_transaction_risk(transaction)
        elapsed = (time.perf_counter() - start) * 1000
        
        print(f"  Risk Level: {signal.risk_level.value}")
        print(f"  Risk Score: {signal.risk_score:.3f}")
        print(f"  Reasons: {signal.risk_reasons}")
        print(f"  Time: {elapsed:.2f}ms")
        
        # Test batch assessment
        print(f"\nBatch assessment (50 transactions)...")
        transactions = [
            {
                "amount": 500 + i * 200,
                "vendor": f"Vendor_{i % 10}",
                "category": ["office", "travel", "consulting"][i % 3],
                "employee_id": f"emp_{i % 5}",
            }
            for i in range(50)
        ]
        
        start = time.perf_counter()
        results = service.batch_assess(transactions)
        batch_elapsed = (time.perf_counter() - start) * 1000
        
        print(f"  Total time: {batch_elapsed:.2f}ms")
        print(f"  Per transaction: {batch_elapsed/50:.2f}ms")
        print(f"  Inference mode: {results[0].get('inference_mode', 'unknown')}")
        
        # Show distribution
        high_risk = sum(1 for r in results if r["risk_signal"]["risk_level"] == "HIGH")
        medium_risk = sum(1 for r in results if r["risk_signal"]["risk_level"] == "MEDIUM")
        low_risk = sum(1 for r in results if r["risk_signal"]["risk_level"] == "LOW")
        print(f"  Distribution: {high_risk} HIGH, {medium_risk} MEDIUM, {low_risk} LOW")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all GPU tests."""
    print("="*60)
    print("🚀 ArmorIQ GPU Acceleration Test Suite")
    print("="*60)
    print("\nTesting NVIDIA CUDA acceleration capabilities...\n")
    
    results = {
        "Device Detection": test_device_detection(),
        "GNN Risk Model": test_gnn_risk_model(),
        "Batch Inference": test_batch_inference(),
        "Vector Operations": test_vector_operations(),
        "Risk Service": test_risk_service_integration(),
    }
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All GPU acceleration tests passed!")
    elif passed > 0:
        print("\n⚠️ Some tests passed - GPU partially available")
    else:
        print("\n⚠️ GPU acceleration unavailable - using CPU fallback")
    
    print("\n" + "="*60)
    print("GPU Installation Guide:")
    print("="*60)
    print("""
To enable full GPU acceleration:

1. Install PyTorch with CUDA:
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

2. Install PyTorch Geometric:
   pip install torch-geometric

3. Install FAISS-GPU (optional, for vector search):
   pip install faiss-gpu

4. Install CuPy (optional, for array ops):
   pip install cupy-cuda12x

5. Verify CUDA is available:
   python -c "import torch; print(torch.cuda.is_available())"
""")


if __name__ == "__main__":
    main()
