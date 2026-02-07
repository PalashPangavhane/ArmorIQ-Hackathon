"""
Test script for GraphRAG Pipeline

Tests the State-of-the-Art hybrid RAG system with:
- Entity extraction
- Knowledge graph building
- Graph + vector retrieval
"""

import sys
sys.path.insert(0, r'c:\Users\palas\ArmorIQ-Hackathon')

from src.intelligence.graph_rag import (
    EntityExtractor,
    KnowledgeGraph,
    GraphRetriever,
    HybridRAGPipeline,
    create_hybrid_rag_pipeline,
    RetrievalStrategy
)
from src.intelligence.llm import OllamaService
from src.intelligence.rag.embedding_service import EmbeddingService


# Sample payment approval policy document
SAMPLE_DOCUMENT = """
Payment Approval Policy - ArmorIQ Financial Systems

1. Authorization Levels

1.1 Employee Level (Tier 1)
Employees can approve payments up to $500 without additional authorization.
All employees must complete security awareness training before gaining approval rights.

1.2 Manager Level (Tier 2)
Department managers can approve payments between $500 and $5,000.
Managers include: John Smith (Engineering), Sarah Johnson (Marketing), Mike Chen (Finance).
All manager approvals are logged in the audit system.

1.3 Director Level (Tier 3)
Directors can approve payments between $5,000 and $25,000.
Current directors: Emily Davis (VP Engineering), Robert Wilson (VP Operations).
Director approvals require business justification documentation.

1.4 Executive Level (Tier 4)
CFO and CEO can approve payments above $25,000.
CFO: James Anderson
CEO: Lisa Thompson
Payments above $100,000 require board notification.

2. Vendor Management

2.1 Approved Vendors
- Acme Supplies Inc: Office supplies vendor, $50,000 annual contract
- TechCorp Solutions: IT services provider, master service agreement
- Global Logistics Ltd: Shipping and logistics partner
- SecureCloud Systems: Cloud infrastructure provider, SOC2 certified

2.2 Vendor Onboarding
New vendors require:
- W-9 tax documentation
- Certificate of insurance
- Background check completion
- Payment terms agreement (Net 30 standard)

3. Fraud Detection Rules

3.1 Automatic Flags
- Payments to new vendors above $10,000
- Multiple payments to same vendor within 24 hours exceeding $15,000
- Payments outside normal business hours (6 PM - 6 AM)
- International wire transfers above $5,000

3.2 Investigation Protocol
Flagged payments are reviewed by the Security Team within 4 hours.
Security Team Lead: Patricia Martinez
High-risk flags escalate to CFO James Anderson immediately.
"""


def test_entity_extraction():
    """Test entity extraction from documents."""
    print("\n" + "="*60)
    print("TEST 1: Entity Extraction")
    print("="*60)
    
    llm_service = OllamaService()
    extractor = EntityExtractor(llm_service)
    
    # Extract from sample document
    print("\nExtracting entities from payment policy document...")
    entities, relationships = extractor.extract_from_text(
        SAMPLE_DOCUMENT,
        chunk_id="payment_policy_v1"
    )
    
    print(f"\nExtracted {len(entities)} entities:")
    for entity in entities[:10]:
        desc = entity.description[:50] if entity.description else "No description"
        print(f"  - {entity.name} ({entity.entity_type.value}): {desc}...")
    
    print(f"\nExtracted {len(relationships)} relationships:")
    for rel in relationships[:10]:
        print(f"  - {rel.source} --[{rel.type}]--> {rel.target}")
    
    return entities, relationships


def test_knowledge_graph(entities, relationships):
    """Test knowledge graph construction."""
    print("\n" + "="*60)
    print("TEST 2: Knowledge Graph Construction")
    print("="*60)
    
    kg = KnowledgeGraph()
    embedding_service = EmbeddingService()
    
    # Add entities
    print("\nBuilding knowledge graph...")
    entity_id_map = {}
    
    for entity in entities:
        desc = entity.description if entity.description else entity.name
        emb = embedding_service.generate_embedding(f"{entity.name}: {desc}")
        node_id = kg.add_entity(entity, embedding=emb)
        entity_id_map[entity.name] = node_id
    
    # Add relationships
    for rel in relationships:
        source_id = entity_id_map.get(rel.source_entity_id)
        target_id = entity_id_map.get(rel.target_entity_id)
        if source_id and target_id:
            kg.add_relationship(
                source_id=source_id,
                target_id=target_id,
                rel_type=rel.relationship_type.replace(" ", "_").upper()
            )
    
    print(f"\nGraph Statistics:")
    print(f"  - Nodes: {len(kg._node_index)}")
    print(f"  - Edges: {kg.graph.number_of_edges()}")
    
    # Test graph operations
    print("\nTesting graph operations...")
    
    # Find a node
    test_node = kg.get_node_by_name("John Smith")
    if test_node:
        print(f"  - Found node: {test_node.name} ({test_node.node_type})")
        
        # Get neighbors
        neighbors = kg.get_neighbors(test_node.id, max_depth=1)
        print(f"  - Neighbors: {[n[0].name for n in neighbors[:5]]}")
    
    # Calculate centrality
    centrality = kg.calculate_centrality()
    if centrality:
        sorted_centrality = sorted(centrality.items(), key=lambda x: x[1], reverse=True)
        print("\n  Top 5 central entities:")
        for node_id, score in sorted_centrality[:5]:
            node = kg._node_index.get(node_id)
            if node:
                print(f"    - {node.name}: {score:.4f}")
    
    return kg


def test_graph_retriever(kg):
    """Test graph-based retrieval."""
    print("\n" + "="*60)
    print("TEST 3: Graph Retrieval")
    print("="*60)
    
    embedding_service = EmbeddingService()
    retriever = GraphRetriever(
        knowledge_graph=kg,
        embedding_service=embedding_service,
        graph_expansion_depth=2
    )
    
    queries = [
        "Who can approve payments above $10,000?",
        "What are the fraud detection rules?",
        "Tell me about vendor Acme Supplies"
    ]
    
    for query in queries:
        print(f"\nQuery: {query}")
        context = retriever.retrieve(query, top_k=5)
        
        print(f"  - Direct matches: {len(context.direct_matches)}")
        print(f"  - Graph entities: {len(context.graph_entities)}")
        print(f"  - Confidence: {context.confidence:.2f}")
        
        if context.direct_matches:
            print(f"  - Top match: {context.direct_matches[0].get('name', 'N/A')}")
    
    return retriever


def test_hybrid_rag():
    """Test full hybrid RAG pipeline."""
    print("\n" + "="*60)
    print("TEST 4: Hybrid RAG Pipeline")
    print("="*60)
    
    # Create pipeline (without Neo4j for simplicity)
    pipeline = create_hybrid_rag_pipeline(use_neo4j=False)
    
    print("\nIngesting document into hybrid pipeline...")
    pipeline.ingest_document(
        text=SAMPLE_DOCUMENT,
        doc_id="payment_policy_v1",
        metadata={"version": "1.0", "type": "policy"}
    )
    
    print(f"Pipeline stats: {pipeline.get_stats()}")
    
    # Test queries
    queries = [
        "Who is the CFO and what is their approval limit?",
        "What happens when a payment is flagged for fraud?",
        "Which vendors are approved for cloud services?"
    ]
    
    for query in queries:
        print(f"\n{'='*50}")
        print(f"Question: {query}")
        print("-"*50)
        
        response = pipeline.query(
            question=query,
            strategy=RetrievalStrategy.HYBRID,
            top_k=5
        )
        
        print(f"\nAnswer: {response.answer}")
        print(f"\nConfidence: {response.confidence:.2f}")
        print(f"Strategy: {response.retrieval_strategy}")
        print(f"Sources: {len(response.sources)}")


def main():
    print("="*60)
    print("ArmorIQ GraphRAG Pipeline Test Suite")
    print("Testing State-of-the-Art Graph-based RAG")
    print("="*60)
    
    try:
        # Test 1: Entity Extraction
        entities, relationships = test_entity_extraction()
        
        if not entities:
            print("\nNo entities extracted. Check LLM service.")
            return
        
        # Test 2: Knowledge Graph
        kg = test_knowledge_graph(entities, relationships)
        
        # Test 3: Graph Retriever
        retriever = test_graph_retriever(kg)
        
        # Test 4: Full Hybrid RAG
        test_hybrid_rag()
        
        print("\n" + "="*60)
        print("ALL TESTS COMPLETED SUCCESSFULLY!")
        print("="*60)
        
    except Exception as e:
        print(f"\nError during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
