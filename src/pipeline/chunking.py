"""
Adaptive chunking strategy for financial documents.

Features:
- Semantic boundary detection (preserves sentences)
- Ticker extraction
- Metadata enrichment
"""

import logging
import re
from typing import Any, List, Dict

import nltk

logger = logging.getLogger(__name__)

# Ensure NLTK data is available
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt', quiet=True)
    nltk.download('punkt_tab', quiet=True)


class AdaptiveChunker:
    """
    Smart chunker that respects semantic boundaries and extracts financial metadata.
    """

    def __init__(self, max_chunk_size: int = 512, overlap: int = 50):
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
        
        # Common ticker pattern: 1-5 uppercase letters
        self.ticker_pattern = re.compile(r'\b[A-Z]{1,5}\b')

    def chunk_document(self, content: str, title: str = "") -> List[Dict[str, Any]]:
        """
        Chunk a document with metadata extraction.

        Args:
            content: Document body text
            title: Document title (optional)

        Returns:
            List of chunks with text and metadata
        """
        full_text = f"{title}\n{content}" if title else content
        if not full_text.strip():
            return []

        # Split into semantic units (sentences)
        sentences = self._split_sentences(full_text)
        
        chunks: List[Dict[str, Any]] = []
        current_chunk: List[str] = []
        current_length = 0
        
        for sentence in sentences:
            # Estimate token count (simple splitting)
            sentence_length = len(sentence.split())
            
            if current_length + sentence_length > self.max_chunk_size:
                if current_chunk:
                    chunk_text = " ".join(current_chunk)
                    chunks.append(self._enrich_chunk(chunk_text))
                
                # Start new chunk with overlap if needed (not implemented here for simplicity, 
                # but could add last N sentences of previous chunk)
                current_chunk = [sentence]
                current_length = sentence_length
            else:
                current_chunk.append(sentence)
                current_length += sentence_length
        
        # Add final chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunks.append(self._enrich_chunk(chunk_text))
            
        return chunks

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences using NLTK or regex fallback."""
        try:
            return nltk.sent_tokenize(text)
        except Exception as e:
            logger.warning(f"NLTK sent_tokenize failed: {e}, using regex fallback")
            return re.split(r'(?<=[.!?])\s+', text)

    def _enrich_chunk(self, text: str) -> Dict[str, Any]:
        """Add metadata to chunk."""
        tickers = self._extract_tickers(text)
        
        return {
            "text": text,
            "metadata": {
                "tickers": tickers,
                "char_length": len(text),
                "token_estimate": len(text.split())
            }
        }

    def _extract_tickers(self, text: str) -> List[str]:
        """Extract potential stock tickers from text."""
        # This is a naive implementation. In production, check against a known list.
        candidates = self.ticker_pattern.findall(text)
        
        # Filter for likely tickers (e.g., AAPL, MSFT) vs common words (I, A, THE)
        # Using a small stoplist of common uppercase words in finance news
        common_words = {'I', 'A', 'PM', 'AM', 'US', 'UK', 'EU', 'CEO', 'CFO', 'CTO', 'FY', 'Q1', 'Q2', 'Q3', 'Q4', 'EPS'}
        return list(set(c for c in candidates if c not in common_words and len(c) > 1))
