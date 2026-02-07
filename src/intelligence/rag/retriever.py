"""
Retriever Module

Handles contextual retrieval of financial information
to support agent reasoning with grounded knowledge.

Answers questions like:
- Remaining department budget
- Historical reimbursement averages
- Vendor legitimacy
- Spending patterns
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from .embedding_service import EmbeddingService
from .vector_store import VectorStore


class ContextType(Enum):
    """Types of context that can be retrieved."""
    BUDGET = "budget"
    VENDOR = "vendor"
    EXPENSE = "expense"
    POLICY = "policy"
    EMPLOYEE = "employee"
    AUDIT = "audit"
    GENERAL = "general"


@dataclass
class RetrievalResult:
    """Result from a retrieval query."""
    query: str
    context_type: ContextType
    documents: List[Dict[str, Any]]
    total_found: int
    confidence: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "context_type": self.context_type.value,
            "documents": self.documents,
            "total_found": self.total_found,
            "confidence": self.confidence
        }
    
    def get_combined_context(self, max_length: int = 4000) -> str:
        """Get combined text context from all documents."""
        texts = []
        current_length = 0
        
        for doc in self.documents:
            content = doc.get('content', '')
            if current_length + len(content) <= max_length:
                texts.append(content)
                current_length += len(content)
            else:
                # Add partial content
                remaining = max_length - current_length
                if remaining > 100:
                    texts.append(content[:remaining] + "...")
                break
        
        return "\n\n---\n\n".join(texts)


class FinancialRetriever:
    """Retrieves relevant financial context for agent queries."""
    
    def __init__(
        self, 
        embedding_service: EmbeddingService,
        vector_store: VectorStore,
        default_top_k: int = 5,
        similarity_threshold: float = 0.5
    ):
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.default_top_k = default_top_k
        self.similarity_threshold = similarity_threshold
    
    def retrieve(
        self, 
        query: str, 
        top_k: Optional[int] = None,
        context_type: Optional[ContextType] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> RetrievalResult:
        """
        Retrieve relevant financial documents for a query.
        
        Args:
            query: Natural language query
            top_k: Number of documents to retrieve
            context_type: Optional filter by context type
            filters: Additional metadata filters
            
        Returns:
            RetrievalResult with relevant documents
        """
        top_k = top_k or self.default_top_k
        
        # Build filters
        search_filters = filters or {}
        if context_type:
            search_filters["context_type"] = context_type.value
        
        # Generate query embedding
        query_embedding = self.embedding_service.generate_query_embedding(query)
        
        # Search vector store
        results = self.vector_store.similarity_search(
            query_embedding=query_embedding,
            top_k=top_k,
            filters=search_filters if search_filters else None
        )
        
        # Filter by similarity threshold
        filtered_results = [
            doc for doc in results 
            if doc.get('similarity_score', 0) >= self.similarity_threshold
        ]
        
        # Calculate confidence based on top result similarity
        confidence = 0.0
        if filtered_results:
            top_similarity = filtered_results[0].get('similarity_score', 0)
            confidence = min(top_similarity, 1.0)
        
        return RetrievalResult(
            query=query,
            context_type=context_type or ContextType.GENERAL,
            documents=filtered_results,
            total_found=len(filtered_results),
            confidence=confidence
        )
    
    def get_budget_context(
        self, 
        department: str,
        fiscal_year: Optional[str] = None
    ) -> RetrievalResult:
        """
        Retrieve budget information for a department.
        
        Args:
            department: Department name
            fiscal_year: Optional fiscal year filter
            
        Returns:
            Budget-related documents and context
        """
        query = f"budget allocation spending limit for {department} department"
        if fiscal_year:
            query += f" fiscal year {fiscal_year}"
        
        filters = {"document_type": "budget"}
        
        return self.retrieve(
            query=query,
            context_type=ContextType.BUDGET,
            filters=filters
        )
    
    def get_vendor_context(
        self, 
        vendor_id: Optional[str] = None,
        vendor_name: Optional[str] = None
    ) -> RetrievalResult:
        """
        Retrieve vendor history and legitimacy information.
        
        Args:
            vendor_id: Vendor identifier
            vendor_name: Vendor name for search
            
        Returns:
            Vendor-related documents
        """
        if vendor_id:
            query = f"vendor information history for vendor ID {vendor_id}"
        elif vendor_name:
            query = f"vendor information history for {vendor_name}"
        else:
            raise ValueError("Either vendor_id or vendor_name must be provided")
        
        return self.retrieve(
            query=query,
            context_type=ContextType.VENDOR
        )
    
    def get_spending_history(
        self, 
        employee_id: str, 
        time_range: Optional[str] = None,
        category: Optional[str] = None
    ) -> RetrievalResult:
        """
        Retrieve employee spending history.
        
        Args:
            employee_id: Employee identifier
            time_range: Optional time range (e.g., "last 6 months")
            category: Optional expense category filter
            
        Returns:
            Employee expense history documents
        """
        query = f"expense history reimbursements for employee {employee_id}"
        if time_range:
            query += f" {time_range}"
        if category:
            query += f" category {category}"
        
        return self.retrieve(
            query=query,
            context_type=ContextType.EXPENSE
        )
    
    def get_policy_context(
        self,
        policy_type: Optional[str] = None,
        amount: Optional[float] = None
    ) -> RetrievalResult:
        """
        Retrieve relevant policy documents.
        
        Args:
            policy_type: Type of policy (expense, approval, travel, etc.)
            amount: Transaction amount for relevant threshold policies
            
        Returns:
            Policy documents
        """
        query = "company policy guidelines"
        if policy_type:
            query = f"{policy_type} policy guidelines rules"
        if amount:
            query += f" for amount ${amount}"
        
        return self.retrieve(
            query=query,
            context_type=ContextType.POLICY
        )
    
    def get_similar_transactions(
        self,
        description: str,
        amount: float,
        category: str,
        top_k: int = 10
    ) -> RetrievalResult:
        """
        Find similar historical transactions.
        
        Args:
            description: Transaction description
            amount: Transaction amount
            category: Expense category
            top_k: Number of similar transactions
            
        Returns:
            Similar historical transactions
        """
        query = f"transaction expense {category} {description} amount similar to ${amount}"
        
        return self.retrieve(
            query=query,
            top_k=top_k,
            context_type=ContextType.EXPENSE
        )
    
    def multi_retrieve(
        self,
        queries: List[Dict[str, Any]]
    ) -> Dict[str, RetrievalResult]:
        """
        Perform multiple retrieval queries efficiently.
        
        Args:
            queries: List of query configurations
                Each dict should have: 'name', 'query', and optionally 'context_type', 'top_k'
            
        Returns:
            Dictionary mapping query names to results
        """
        results = {}
        
        for query_config in queries:
            name = query_config.get('name', query_config.get('query', 'unnamed'))
            query = query_config.get('query', '')
            context_type = query_config.get('context_type')
            top_k = query_config.get('top_k', self.default_top_k)
            
            if isinstance(context_type, str):
                context_type = ContextType(context_type)
            
            results[name] = self.retrieve(
                query=query,
                top_k=top_k,
                context_type=context_type
            )
        
        return results
    
    def get_comprehensive_context(
        self,
        employee_id: str,
        department: str,
        amount: float,
        category: str,
        vendor_id: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, RetrievalResult]:
        """
        Get comprehensive context for a payment request.
        
        This is the main method used by agents to gather all relevant
        context for making a decision on a payment request.
        
        Returns:
            Dictionary with budget, policy, history, and optionally vendor context
        """
        queries = [
            {
                "name": "budget",
                "query": f"budget allocation for {department} department remaining balance",
                "context_type": ContextType.BUDGET
            },
            {
                "name": "policy",
                "query": f"expense policy approval limits for {category} category amount ${amount}",
                "context_type": ContextType.POLICY
            },
            {
                "name": "employee_history",
                "query": f"expense history for employee {employee_id} {category}",
                "context_type": ContextType.EXPENSE
            }
        ]
        
        if vendor_id:
            queries.append({
                "name": "vendor",
                "query": f"vendor {vendor_id} history legitimacy approved",
                "context_type": ContextType.VENDOR
            })
        
        if description:
            queries.append({
                "name": "similar_transactions",
                "query": f"similar expense {category} {description}",
                "context_type": ContextType.EXPENSE,
                "top_k": 3
            })
        
        return self.multi_retrieve(queries)
