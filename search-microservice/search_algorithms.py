"""
Search Algorithms Module

Implements Strategy Pattern for extensible search algorithms.
New algorithms can be added by extending the SearchAlgorithm base class.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class SearchAlgorithm(ABC):
    """Abstract base class for search algorithms."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of the algorithm."""
        pass
    
    @abstractmethod
    def search(self, query: str, videos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Perform search on the given videos.
        
        Args:
            query: Search query string
            videos: List of video dictionaries with 'id', 'title', 'description'
        
        Returns:
            List of search results with format:
            [
                {
                    'video_id': int,
                    'title': str,
                    'relevance_score': float (0-1),
                    'matched_text': str
                }
            ]
        """
        pass


class TextSearchAlgorithm(SearchAlgorithm):
    """
    Text-based search algorithm using keyword matching.
    Searches in video titles and descriptions.
    """
    
    @property
    def name(self) -> str:
        return "text_search"
    
    def search(self, query: str, videos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not query:
            return []
        
        query_lower = query.lower()
        query_words = query_lower.split()
        results = []
        
        for video in videos:
            score = 0.0
            matched_parts = []
            
            # Check title matches
            title = video.get('title', '')
            title_lower = title.lower()
            
            if query_lower in title_lower:
                score += 0.7
                matched_parts.append(title)
            else:
                # Check for word matches in title
                for word in query_words:
                    if word in title_lower:
                        score += 0.3 / len(query_words)
                        if title not in matched_parts:
                            matched_parts.append(title)
            
            # Check description matches
            description = video.get('description', '') or ''
            description_lower = description.lower()
            
            if query_lower in description_lower:
                score += 0.3
                # Extract snippet from description
                idx = description_lower.find(query_lower)
                start = max(0, idx - 30)
                end = min(len(description), idx + len(query) + 30)
                snippet = description[start:end]
                if snippet and snippet not in matched_parts:
                    matched_parts.append(f"...{snippet}...")
            else:
                # Check for word matches in description
                for word in query_words:
                    if word in description_lower:
                        score += 0.1 / len(query_words)
            
            if score > 0:
                results.append({
                    'video_id': video.get('id'),
                    'title': title,
                    'relevance_score': min(1.0, score),
                    'matched_text': matched_parts[0] if matched_parts else title
                })
        
        # Sort by relevance score (descending)
        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        return results


class FuzzySearchAlgorithm(SearchAlgorithm):
    """
    Fuzzy search algorithm with typo tolerance.
    Uses simple character-based similarity.
    """
    
    @property
    def name(self) -> str:
        return "fuzzy_search"
    
    def _similarity(self, s1: str, s2: str) -> float:
        """Calculate simple similarity ratio between two strings."""
        if not s1 or not s2:
            return 0.0
        
        s1_lower = s1.lower()
        s2_lower = s2.lower()
        
        # Check if one is substring of another
        if s1_lower in s2_lower or s2_lower in s1_lower:
            return 0.9
        
        # Count matching characters
        matches = sum(1 for c in s1_lower if c in s2_lower)
        return matches / max(len(s1_lower), len(s2_lower))
    
    def search(self, query: str, videos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not query:
            return []
        
        results = []
        
        for video in videos:
            title = video.get('title', '')
            description = video.get('description', '') or ''
            
            title_sim = self._similarity(query, title)
            desc_sim = self._similarity(query, description)
            
            score = max(title_sim * 0.7, desc_sim * 0.3)
            
            if score > 0.2:  # Threshold
                results.append({
                    'video_id': video.get('id'),
                    'title': title,
                    'relevance_score': min(1.0, score),
                    'matched_text': title if title_sim >= desc_sim else description[:50]
                })
        
        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        return results


class SearchAlgorithmFactory:
    """Factory for creating search algorithm instances."""
    
    _algorithms = {
        'text_search': TextSearchAlgorithm,
        'fuzzy_search': FuzzySearchAlgorithm,
    }
    
    @classmethod
    def get_algorithm(cls, name: str = 'text_search') -> SearchAlgorithm:
        """
        Get a search algorithm instance by name.
        
        Args:
            name: Algorithm name ('text_search', 'fuzzy_search')
        
        Returns:
            SearchAlgorithm instance
        """
        algorithm_class = cls._algorithms.get(name, TextSearchAlgorithm)
        return algorithm_class()
    
    @classmethod
    def register_algorithm(cls, name: str, algorithm_class: type):
        """Register a new algorithm type."""
        cls._algorithms[name] = algorithm_class
    
    @classmethod
    def list_algorithms(cls) -> List[str]:
        """List all available algorithm names."""
        return list(cls._algorithms.keys())
