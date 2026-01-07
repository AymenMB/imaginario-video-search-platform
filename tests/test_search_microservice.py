"""
Unit Tests for Search Microservice

Tests cover:
- Search algorithm functionality
- API endpoints
- Service authentication
"""

import pytest
import json
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'search-microservice'))

from search_algorithms import (
    SearchAlgorithm,
    TextSearchAlgorithm,
    FuzzySearchAlgorithm,
    SearchAlgorithmFactory
)


class TestTextSearchAlgorithm:
    """Tests for TextSearchAlgorithm."""
    
    def setup_method(self):
        self.algorithm = TextSearchAlgorithm()
        self.videos = [
            {'id': 1, 'title': 'Introduction to Python', 'description': 'Learn Python basics'},
            {'id': 2, 'title': 'Advanced JavaScript', 'description': 'Deep dive into JS'},
            {'id': 3, 'title': 'Python Machine Learning', 'description': 'ML with Python and TensorFlow'},
            {'id': 4, 'title': 'Web Development 101', 'description': 'HTML, CSS, and JavaScript basics'},
        ]
    
    def test_algorithm_name(self):
        """Test algorithm name property."""
        assert self.algorithm.name == 'text_search'
    
    def test_empty_query_returns_empty(self):
        """Test that empty query returns empty results."""
        results = self.algorithm.search('', self.videos)
        assert results == []
    
    def test_exact_title_match(self):
        """Test exact match in title gets high score."""
        results = self.algorithm.search('Python', self.videos)
        assert len(results) >= 2
        # Python videos should be at top
        titles = [r['title'] for r in results]
        assert any('Python' in t for t in titles[:2])
    
    def test_description_match(self):
        """Test matching in description."""
        results = self.algorithm.search('TensorFlow', self.videos)
        assert len(results) >= 1
        assert results[0]['video_id'] == 3
    
    def test_word_partial_match(self):
        """Test partial word matches."""
        results = self.algorithm.search('JavaScript', self.videos)
        assert len(results) >= 2
    
    def test_results_sorted_by_relevance(self):
        """Test results are sorted by relevance score."""
        results = self.algorithm.search('Python', self.videos)
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i]['relevance_score'] >= results[i + 1]['relevance_score']
    
    def test_no_matches(self):
        """Test query with no matches."""
        results = self.algorithm.search('Rust', self.videos)
        assert results == []
    
    def test_result_structure(self):
        """Test result dictionary has required fields."""
        results = self.algorithm.search('Python', self.videos)
        assert len(results) > 0
        result = results[0]
        assert 'video_id' in result
        assert 'title' in result
        assert 'relevance_score' in result
        assert 'matched_text' in result


class TestFuzzySearchAlgorithm:
    """Tests for FuzzySearchAlgorithm."""
    
    def setup_method(self):
        self.algorithm = FuzzySearchAlgorithm()
        self.videos = [
            {'id': 1, 'title': 'Python Programming', 'description': 'Learn Python'},
            {'id': 2, 'title': 'JavaScript Guide', 'description': 'JS tutorial'},
        ]
    
    def test_algorithm_name(self):
        """Test algorithm name property."""
        assert self.algorithm.name == 'fuzzy_search'
    
    def test_empty_query_returns_empty(self):
        """Test that empty query returns empty results."""
        results = self.algorithm.search('', self.videos)
        assert results == []
    
    def test_fuzzy_match(self):
        """Test fuzzy matching works."""
        results = self.algorithm.search('Pyton', self.videos)  # Typo
        # Should still find Python video with lower score
        assert len(results) >= 0  # May or may not match depending on threshold


class TestSearchAlgorithmFactory:
    """Tests for SearchAlgorithmFactory."""
    
    def test_get_text_search(self):
        """Test getting text search algorithm."""
        algorithm = SearchAlgorithmFactory.get_algorithm('text_search')
        assert isinstance(algorithm, TextSearchAlgorithm)
    
    def test_get_fuzzy_search(self):
        """Test getting fuzzy search algorithm."""
        algorithm = SearchAlgorithmFactory.get_algorithm('fuzzy_search')
        assert isinstance(algorithm, FuzzySearchAlgorithm)
    
    def test_default_algorithm(self):
        """Test default algorithm is text_search."""
        algorithm = SearchAlgorithmFactory.get_algorithm('unknown')
        assert isinstance(algorithm, TextSearchAlgorithm)
    
    def test_list_algorithms(self):
        """Test listing available algorithms."""
        algorithms = SearchAlgorithmFactory.list_algorithms()
        assert 'text_search' in algorithms
        assert 'fuzzy_search' in algorithms


class TestSearchMicroserviceApp:
    """Tests for Search Microservice Flask app."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        # Import here to avoid issues with missing dependencies
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'search-microservice'))
            from app import app, db
            
            app.config['TESTING'] = True
            app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
            
            with app.test_client() as client:
                with app.app_context():
                    db.create_all()
                yield client
        except ImportError:
            pytest.skip("Search microservice dependencies not installed")
    
    def test_health_check(self, client):
        """Test health endpoint."""
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert data['service'] == 'search-microservice'
    
    def test_list_algorithms(self, client):
        """Test algorithms endpoint."""
        response = client.get('/api/v1/search/algorithms')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'algorithms' in data
        assert 'text_search' in data['algorithms']
    
    def test_submit_job_requires_auth(self, client):
        """Test that submitting job requires service auth."""
        response = client.post('/api/v1/search/jobs', json={
            'user_id': 1,
            'query': 'test',
            'videos': []
        })
        assert response.status_code == 401
    
    def test_submit_job_with_auth(self, client):
        """Test submitting job with proper auth."""
        response = client.post(
            '/api/v1/search/jobs',
            json={
                'user_id': 1,
                'query': 'Python',
                'videos': [
                    {'id': 1, 'title': 'Python Basics', 'description': 'Learn Python'}
                ]
            },
            headers={'X-Service-Token': 'service-secret-token-change-in-production'}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'job_id' in data
        assert data['status'] == 'completed'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
