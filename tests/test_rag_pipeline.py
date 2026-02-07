"""
RAG Pipeline Test Suite

Comprehensive tests for the RAG (Retrieval-Augmented Generation) pipeline.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.intelligence.rag.sample_data_generator import SampleDataGenerator
from src.intelligence.rag.document_processor import DocumentProcessor
from src.intelligence.rag.embedding_service import EmbeddingService
from src.intelligence.rag.vector_store import VectorStore
from src.intelligence.rag.retriever import FinancialRetriever, ContextType
from src.intelligence.rag.rag_pipeline import RAGPipeline


def print_section(title: str):
    """Print a section header."""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60 + "\n")


async def test_document_processor():
    """Test the document processor."""
    print_section("Testing Document Processor")
    
    processor = DocumentProcessor(chunk_size=500, chunk_overlap=50)
    
    # Test with a sample text
    sample_text = """
    This is a sample document about expense policies.
    The company requires all expenses over $100 to have receipts.
    Travel expenses must be pre-approved by management.
    Software subscriptions require IT department approval.
    """
    
    # Save sample text to a temp file
    temp_file = Path("./data/temp_test.txt")
    temp_file.parent.mkdir(parents=True, exist_ok=True)
    temp_file.write_text(sample_text)
    
    try:
        # Process the file
        processed = processor.process_file(str(temp_file))
        
        print(f"✓ Processed file: {processed.source_path}")
        print(f"✓ Document type: {processed.doc_type}")
        print(f"✓ Number of chunks: {len(processed.chunks)}")
        
        for i, chunk in enumerate(processed.chunks):
            print(f"\n  Chunk {i+1}:")
            print(f"    Content preview: {chunk.content[:100]}...")
            print(f"    Metadata: {chunk.metadata}")
        
        print("\n✓ Document processor test PASSED")
        return True
    except Exception as e:
        print(f"\n✗ Document processor test FAILED: {e}")
        return False
    finally:
        # Cleanup
        if temp_file.exists():
            temp_file.unlink()


async def test_embedding_service():
    """Test the embedding service."""
    print_section("Testing Embedding Service")
    
    service = EmbeddingService()
    
    test_texts = [
        "What is the travel expense policy?",
        "Maximum hotel rate for business travel",
        "Software subscription approval process"
    ]
    
    try:
        # Test single embedding
        print("Testing single embedding...")
        embedding = await service.generate_embedding(test_texts[0])
        print(f"✓ Generated embedding with {len(embedding)} dimensions")
        
        # Test batch embeddings
        print("\nTesting batch embeddings...")
        embeddings = await service.generate_embeddings_batch(test_texts)
        print(f"✓ Generated {len(embeddings)} embeddings")
        
        # Test query embedding
        print("\nTesting query embedding...")
        query_embedding = await service.generate_query_embedding("expense policy")
        print(f"✓ Generated query embedding with {len(query_embedding)} dimensions")
        
        print("\n✓ Embedding service test PASSED")
        return True
    except Exception as e:
        print(f"\n✗ Embedding service test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_vector_store():
    """Test the vector store."""
    print_section("Testing Vector Store")
    
    # Use a test collection
    store = VectorStore(collection_name="test_collection", persist_directory="./data/test_chroma")
    
    try:
        # Add some test documents
        test_docs = [
            {
                "id": "test1",
                "content": "Travel expenses must be approved by manager before booking",
                "embedding": [0.1] * 768,  # Dummy embedding
                "metadata": {"category": "travel", "type": "policy"}
            },
            {
                "id": "test2",
                "content": "Software purchases require IT approval for amounts over $1000",
                "embedding": [0.2] * 768,
                "metadata": {"category": "software", "type": "policy"}
            },
            {
                "id": "test3",
                "content": "Meal expenses are limited to $50 per person",
                "embedding": [0.3] * 768,
                "metadata": {"category": "meals", "type": "policy"}
            }
        ]
        
        print("Adding documents to vector store...")
        await store.add_documents(test_docs)
        print(f"✓ Added {len(test_docs)} documents")
        
        # Test similarity search
        print("\nTesting similarity search...")
        query_embedding = [0.15] * 768
        results = await store.similarity_search(query_embedding, top_k=2)
        print(f"✓ Retrieved {len(results)} similar documents")
        
        for result in results:
            print(f"  - {result['content'][:50]}... (score: {result['score']:.3f})")
        
        # Test text search
        print("\nTesting text-based search...")
        text_results = await store.search_by_text(
            "travel policy",
            EmbeddingService(),
            top_k=2
        )
        print(f"✓ Text search returned {len(text_results)} results")
        
        # Cleanup test collection
        await store.delete_documents(["test1", "test2", "test3"])
        print("\n✓ Cleaned up test documents")
        
        print("\n✓ Vector store test PASSED")
        return True
    except Exception as e:
        print(f"\n✗ Vector store test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_retriever():
    """Test the financial retriever."""
    print_section("Testing Financial Retriever")
    
    retriever = FinancialRetriever(collection_name="test_retriever")
    
    try:
        # First, add some test documents
        print("Setting up test data...")
        
        test_documents = [
            {
                "id": "budget1",
                "content": "Engineering department has a budget of $500,000 for Q1 2025. Current spending is at 45%.",
                "embedding": [0.1] * 768,
                "metadata": {"type": "budget", "department": "Engineering", "year": "2025"}
            },
            {
                "id": "vendor1",
                "content": "Amazon Business is an approved vendor for office supplies with a risk score of Low.",
                "embedding": [0.2] * 768,
                "metadata": {"type": "vendor", "vendor_name": "Amazon Business", "risk": "low"}
            },
            {
                "id": "policy1",
                "content": "All expenses over $5000 require director approval. VP approval needed for expenses over $25000.",
                "embedding": [0.3] * 768,
                "metadata": {"type": "policy", "category": "approval_thresholds"}
            }
        ]
        
        await retriever.vector_store.add_documents(test_documents)
        print(f"✓ Added {len(test_documents)} test documents")
        
        # Test context retrieval
        print("\nTesting budget context retrieval...")
        budget_context = await retriever.get_budget_context("Engineering department budget")
        print(f"✓ Retrieved {len(budget_context.documents)} budget documents")
        
        print("\nTesting comprehensive context retrieval...")
        comprehensive = await retriever.get_comprehensive_context(
            "Need to approve a $3000 expense for office supplies from Amazon"
        )
        print(f"✓ Retrieved comprehensive context:")
        print(f"  - Budget docs: {len(comprehensive['budget'])}")
        print(f"  - Vendor docs: {len(comprehensive['vendor'])}")
        print(f"  - Policy docs: {len(comprehensive['policy'])}")
        
        # Cleanup
        await retriever.vector_store.delete_documents(["budget1", "vendor1", "policy1"])
        
        print("\n✓ Retriever test PASSED")
        return True
    except Exception as e:
        print(f"\n✗ Retriever test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_full_pipeline():
    """Test the complete RAG pipeline."""
    print_section("Testing Full RAG Pipeline")
    
    try:
        # Generate sample data first
        print("Generating sample data...")
        generator = SampleDataGenerator(output_dir="./data/test_documents")
        generator.generate_all()
        print("✓ Generated sample data")
        
        # Initialize the pipeline
        print("\nInitializing RAG pipeline...")
        pipeline = RAGPipeline(collection_name="test_full_pipeline")
        print("✓ Pipeline initialized")
        
        # Ingest documents
        print("\nIngesting documents...")
        stats = await pipeline.ingest_documents("./data/test_documents")
        print(f"✓ Ingested documents:")
        print(f"  - Total files: {stats['total_files']}")
        print(f"  - Total chunks: {stats['total_chunks']}")
        print(f"  - Embeddings generated: {stats['embeddings_generated']}")
        
        # Test queries
        test_queries = [
            "What is the maximum hotel rate for business travel?",
            "What approval is needed for a $10,000 expense?",
            "Tell me about the Engineering department budget",
            "What are the expense policy guidelines?"
        ]
        
        print("\nTesting queries...")
        for query in test_queries:
            print(f"\n  Query: {query}")
            result = await pipeline.query(query, top_k=3)
            print(f"  Results: {len(result['documents'])} documents")
            if result['documents']:
                print(f"  Top result: {result['documents'][0]['content'][:100]}...")
        
        # Get pipeline stats
        print("\nPipeline statistics:")
        final_stats = await pipeline.get_statistics()
        print(f"  - Total documents: {final_stats['total_documents']}")
        print(f"  - Collection: {final_stats['collection_name']}")
        
        print("\n✓ Full pipeline test PASSED")
        return True
    except Exception as e:
        print(f"\n✗ Full pipeline test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all RAG pipeline tests."""
    print("\n" + "="*60)
    print(" RAG PIPELINE TEST SUITE")
    print("="*60)
    
    results = {}
    
    # Run tests
    results["Document Processor"] = await test_document_processor()
    results["Embedding Service"] = await test_embedding_service()
    results["Vector Store"] = await test_vector_store()
    results["Retriever"] = await test_retriever()
    results["Full Pipeline"] = await test_full_pipeline()
    
    # Summary
    print_section("TEST SUMMARY")
    
    passed = sum(1 for v in results.values() if v)
    failed = sum(1 for v in results.values() if not v)
    
    for test_name, result in results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"  {test_name}: {status}")
    
    print(f"\n  Total: {passed} passed, {failed} failed")
    
    return all(results.values())


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
