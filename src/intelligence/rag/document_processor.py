"""
Document Processor Module

Handles ingestion and chunking of financial documents:
- Financial reports (PDFs)
- Expense ledgers (CSV)
- Vendor records
- Budget documents
- Audit summaries
"""

import os
import csv
import hashlib
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


class DocumentType(Enum):
    PDF = "pdf"
    CSV = "csv"
    TXT = "txt"
    JSON = "json"
    UNKNOWN = "unknown"


@dataclass
class DocumentChunk:
    """Represents a chunk of a processed document."""
    chunk_id: str
    document_id: str
    content: str
    metadata: Dict[str, Any]
    chunk_index: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "content": self.content,
            "metadata": self.metadata,
            "chunk_index": self.chunk_index
        }


@dataclass
class ProcessedDocument:
    """Represents a fully processed document."""
    document_id: str
    filename: str
    document_type: DocumentType
    chunks: List[DocumentChunk]
    metadata: Dict[str, Any]
    processed_at: str


class DocumentProcessor:
    """Processes and chunks financial documents for RAG pipeline."""
    
    def __init__(
        self, 
        chunk_size: int = 512, 
        chunk_overlap: int = 50,
        supported_extensions: Optional[List[str]] = None
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.supported_extensions = supported_extensions or ['.pdf', '.csv', '.txt', '.json']
    
    def process_directory(self, directory_path: str) -> List[ProcessedDocument]:
        """
        Process all supported documents in a directory.
        
        Args:
            directory_path: Path to directory containing documents
            
        Returns:
            List of processed documents
        """
        documents = []
        path = Path(directory_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Directory not found: {directory_path}")
        
        for file_path in path.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in self.supported_extensions:
                try:
                    doc = self.process_file(file_path)
                    if doc:
                        documents.append(doc)
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
        
        return documents
    
    def process_file(self, file_path: Path) -> Optional[ProcessedDocument]:
        """
        Process a single document file.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            ProcessedDocument or None if processing fails
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        document_type = self._detect_document_type(file_path)
        document_id = self._generate_document_id(file_path)
        
        # Extract text based on document type
        if document_type == DocumentType.PDF:
            text, metadata = self._process_pdf(file_path)
        elif document_type == DocumentType.CSV:
            text, metadata = self._process_csv(file_path)
        elif document_type == DocumentType.TXT:
            text, metadata = self._process_txt(file_path)
        elif document_type == DocumentType.JSON:
            text, metadata = self._process_json(file_path)
        else:
            return None
        
        # Create chunks
        chunks = self._create_chunks(text, document_id, metadata)
        
        return ProcessedDocument(
            document_id=document_id,
            filename=file_path.name,
            document_type=document_type,
            chunks=chunks,
            metadata={
                **metadata,
                "file_path": str(file_path),
                "file_size": file_path.stat().st_size
            },
            processed_at=datetime.utcnow().isoformat()
        )
    
    def _detect_document_type(self, file_path: Path) -> DocumentType:
        """Detect document type from file extension."""
        ext = file_path.suffix.lower()
        type_map = {
            '.pdf': DocumentType.PDF,
            '.csv': DocumentType.CSV,
            '.txt': DocumentType.TXT,
            '.json': DocumentType.JSON
        }
        return type_map.get(ext, DocumentType.UNKNOWN)
    
    def _generate_document_id(self, file_path: Path) -> str:
        """Generate unique document ID based on file path and content hash."""
        content = file_path.read_bytes()
        hash_value = hashlib.md5(content).hexdigest()[:12]
        return f"doc_{file_path.stem}_{hash_value}"
    
    def _process_pdf(self, file_path: Path) -> tuple[str, Dict[str, Any]]:
        """Extract text from PDF documents."""
        try:
            from pypdf import PdfReader
            
            reader = PdfReader(str(file_path))
            text_parts = []
            
            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"[Page {page_num + 1}]\n{page_text}")
            
            text = "\n\n".join(text_parts)
            metadata = {
                "document_type": "pdf",
                "page_count": len(reader.pages),
                "has_images": any(page.images for page in reader.pages)
            }
            
            return text, metadata
            
        except ImportError:
            raise ImportError("pypdf is required for PDF processing. Install with: pip install pypdf")
    
    def _process_csv(self, file_path: Path) -> tuple[str, Dict[str, Any]]:
        """Process CSV expense ledgers and convert to text."""
        text_parts = []
        row_count = 0
        headers = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            
            for row in reader:
                row_count += 1
                # Convert each row to a readable format
                row_text = " | ".join([f"{k}: {v}" for k, v in row.items() if v])
                text_parts.append(row_text)
        
        # Create structured text representation
        header_text = f"Columns: {', '.join(headers)}\n\n"
        text = header_text + "\n".join(text_parts)
        
        metadata = {
            "document_type": "csv",
            "row_count": row_count,
            "columns": headers
        }
        
        return text, metadata
    
    def _process_txt(self, file_path: Path) -> tuple[str, Dict[str, Any]]:
        """Process plain text documents."""
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        metadata = {
            "document_type": "txt",
            "char_count": len(text),
            "line_count": text.count('\n') + 1
        }
        
        return text, metadata
    
    def _process_json(self, file_path: Path) -> tuple[str, Dict[str, Any]]:
        """Process JSON documents."""
        import json
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Convert JSON to readable text format
        text = self._json_to_text(data)
        
        metadata = {
            "document_type": "json",
            "is_array": isinstance(data, list),
            "top_level_keys": list(data.keys()) if isinstance(data, dict) else []
        }
        
        return text, metadata
    
    def _json_to_text(self, data: Any, prefix: str = "") -> str:
        """Convert JSON data to readable text format."""
        lines = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    lines.append(f"{prefix}{key}:")
                    lines.append(self._json_to_text(value, prefix + "  "))
                else:
                    lines.append(f"{prefix}{key}: {value}")
        elif isinstance(data, list):
            for i, item in enumerate(data):
                lines.append(f"{prefix}Item {i + 1}:")
                lines.append(self._json_to_text(item, prefix + "  "))
        else:
            lines.append(f"{prefix}{data}")
        
        return "\n".join(lines)
    
    def _create_chunks(
        self, 
        text: str, 
        document_id: str,
        base_metadata: Dict[str, Any]
    ) -> List[DocumentChunk]:
        """
        Split text into overlapping chunks.
        
        Uses sentence-aware chunking to avoid breaking mid-sentence.
        """
        if not text.strip():
            return []
        
        # Clean text
        text = self._clean_text(text)
        
        # Split into sentences first
        sentences = self._split_into_sentences(text)
        
        chunks = []
        current_chunk = []
        current_length = 0
        chunk_index = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            # If adding this sentence exceeds chunk size
            if current_length + sentence_length > self.chunk_size and current_chunk:
                # Create chunk from current content
                chunk_text = " ".join(current_chunk)
                chunk_id = f"{document_id}_chunk_{chunk_index}"
                
                chunks.append(DocumentChunk(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    content=chunk_text,
                    metadata={
                        **base_metadata,
                        "chunk_index": chunk_index,
                        "chunk_length": len(chunk_text)
                    },
                    chunk_index=chunk_index
                ))
                
                chunk_index += 1
                
                # Keep overlap by retaining some sentences
                overlap_sentences = []
                overlap_length = 0
                for s in reversed(current_chunk):
                    if overlap_length + len(s) <= self.chunk_overlap:
                        overlap_sentences.insert(0, s)
                        overlap_length += len(s)
                    else:
                        break
                
                current_chunk = overlap_sentences
                current_length = overlap_length
            
            current_chunk.append(sentence)
            current_length += sentence_length
        
        # Don't forget the last chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunk_id = f"{document_id}_chunk_{chunk_index}"
            
            chunks.append(DocumentChunk(
                chunk_id=chunk_id,
                document_id=document_id,
                content=chunk_text,
                metadata={
                    **base_metadata,
                    "chunk_index": chunk_index,
                    "chunk_length": len(chunk_text)
                },
                chunk_index=chunk_index
            ))
        
        return chunks
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        import re
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep punctuation
        text = re.sub(r'[^\w\s.,!?;:\-\'"$%@#&*()\[\]{}/<>]', '', text)
        return text.strip()
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        import re
        
        # Simple sentence splitting
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def process_text_directly(
        self, 
        text: str, 
        document_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[DocumentChunk]:
        """
        Process raw text directly without file.
        Useful for processing API responses or database content.
        """
        metadata = metadata or {}
        metadata["document_type"] = "text"
        metadata["source"] = "direct_input"
        
        return self._create_chunks(text, document_id, metadata)
