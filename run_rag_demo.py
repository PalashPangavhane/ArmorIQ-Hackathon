"""
RAG Pipeline Demo Script

This script demonstrates the complete RAG pipeline workflow:
1. Generate sample financial data
2. Ingest documents into vector store
3. Query the knowledge base
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
# Load environment variables
from dotenv import load_dotenv
load_dotenv(project_root / ".env")
from src.intelligence.rag import (
    RAGPipeline,
    SampleDataGenerator,
    generate_sample_data
)


async def main():
    print("="*60)
    print(" ArmorIQ RAG Pipeline Demo")
    print("="*60)
    
    # Step 1: Generate sample data
    print("\n[Step 1] Generating sample financial data...")
    generator = SampleDataGenerator(output_dir="./data/documents")
    files = generator.generate_all()
    print(f"✓ Generated data in: {list(files.keys())}")
    
    # Step 2: Initialize RAG pipeline
    print("\n[Step 2] Initializing RAG pipeline...")
    pipeline = RAGPipeline(
        collection_name="armoriq_knowledge_base",
        persist_directory="./data/embeddings/chroma"
    )
    print("✓ Pipeline initialized")
    
    # Step 3: Ingest documents
    print("\n[Step 3] Ingesting documents into vector store...")
    print("  (This may take a moment as embeddings are generated)")
    
    try:
        stats = await pipeline.ingest_documents("./data/documents")
        print(f"\n✓ Ingestion complete:")
        print(f"  - Files processed: {stats['total_files']}")
        print(f"  - Chunks created: {stats['total_chunks']}")
        print(f"  - Embeddings generated: {stats['embeddings_generated']}")
    except Exception as e:
        print(f"\n⚠ Ingestion encountered an error: {e}")
        print("  This may be due to API rate limits. The pipeline structure is complete.")
        print("  You can retry later when the API quota resets.")
        return
    
    # Step 4: Demo queries
    print("\n[Step 4] Running demo queries...")
    
    demo_queries = [
        "What is the maximum hotel rate for business travel?",
        "What approval is needed for a $15,000 software purchase?",
        "Tell me about the Engineering department budget",
        "What vendors are approved for office supplies?",
        "What are the expense reimbursement policies?"
    ]
    
    for i, query in enumerate(demo_queries, 1):
        print(f"\n--- Query {i}: {query}")
        try:
            result = await pipeline.query(query, top_k=2)
            
            if result['documents']:
                print(f"  Found {len(result['documents'])} relevant documents:")
                for j, doc in enumerate(result['documents'][:2], 1):
                    content = doc['content'][:150].replace('\n', ' ')
                    print(f"  [{j}] {content}...")
            else:
                print("  No relevant documents found.")
        except Exception as e:
            print(f"  Error: {e}")
    
    # Step 5: Show statistics
    print("\n[Step 5] Pipeline Statistics")
    try:
        stats = await pipeline.get_statistics()
        print(f"  - Collection: {stats['collection_name']}")
        print(f"  - Total documents: {stats['total_documents']}")
        print(f"  - Embedding dimensions: {stats['embedding_dimensions']}")
    except Exception as e:
        print(f"  Could not retrieve stats: {e}")
    
    print("\n" + "="*60)
    print(" Demo Complete!")
    print("="*60)
    print("\nThe RAG pipeline is ready. You can now:")
    print("1. Add your own documents to ./data/documents/")
    print("2. Run pipeline.ingest_documents() to process them")
    print("3. Use pipeline.query() to search the knowledge base")
    print("4. Use retriever.get_comprehensive_context() for agent integration")


if __name__ == "__main__":
    asyncio.run(main())
