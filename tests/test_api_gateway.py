"""
Unit Tests for API Gateway

Tests cover:
- Analytics endpoints
- Request logging
- Search service client
"""

import pytest
import json
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api-gateway'))


class TestAPIGatewayApp:
    """Tests for API Gateway Flask app."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        try:
            from app import app, db, User, APIRequestLog, hash_password, generate_jwt_token
            
            app.config['TESTING'] = True
            app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
            
            with app.test_client() as client:
                with app.app_context():
                    db.create_all()
                    
                    # Create test user
                    user = User(
                        email='test@example.com',
                        name='Test User',
                        password_hash=hash_password('password123')
                    )
                    db.session.add(user)
                    db.session.commit()
                    
                    # Store user id and token for tests
                    client.user_id = user.id
                    client.token = generate_jwt_token(user.id)
                    
                    # Add some request logs for analytics tests
                    for i in range(10):
                        log = APIRequestLog(
                            user_id=user.id,
                            endpoint='/api/v1/users/1/videos',
                            method='GET',
                            status_code=200 if i % 3 != 0 else 400,
                            response_time_ms=50 + i * 5,
                            timestamp=datetime.utcnow() - timedelta(days=i)
                        )
                        db.session.add(log)
                    db.session.commit()
                    
                yield client
        except ImportError:
            pytest.skip("API Gateway dependencies not installed")
    
    def test_health_check(self, client):
        """Test health endpoint."""
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert data['service'] == 'api-gateway'
    
    def test_register(self, client):
        """Test user registration."""
        response = client.post('/api/v1/auth/register', json={
            'email': 'newuser@example.com',
            'password': 'password123',
            'name': 'New User'
        })
        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'token' in data
        assert data['user']['email'] == 'newuser@example.com'
    
    def test_login(self, client):
        """Test user login."""
        response = client.post('/api/v1/auth/login', json={
            'email': 'test@example.com',
            'password': 'password123'
        })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'token' in data
    
    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        response = client.post('/api/v1/auth/login', json={
            'email': 'test@example.com',
            'password': 'wrongpassword'
        })
        assert response.status_code == 401
    
    def test_videos_requires_auth(self, client):
        """Test that video endpoints require auth."""
        response = client.get('/api/v1/users/1/videos')
        assert response.status_code == 401
    
    def test_list_videos(self, client):
        """Test listing videos with auth."""
        response = client.get(
            f'/api/v1/users/{client.user_id}/videos',
            headers={'Authorization': f'Bearer {client.token}'}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'videos' in data
    
    def test_create_video(self, client):
        """Test creating a video."""
        response = client.post(
            f'/api/v1/users/{client.user_id}/videos',
            json={'title': 'Test Video', 'description': 'A test video'},
            headers={'Authorization': f'Bearer {client.token}'}
        )
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['title'] == 'Test Video'
    
    def test_analytics_usage(self, client):
        """Test analytics usage endpoint."""
        response = client.get(
            '/api/v1/analytics/usage',
            headers={'Authorization': f'Bearer {client.token}'}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'summary' in data
        assert 'total_requests' in data['summary']
    
    def test_analytics_daily(self, client):
        """Test daily analytics endpoint."""
        response = client.get(
            '/api/v1/analytics/usage/daily',
            headers={'Authorization': f'Bearer {client.token}'}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'daily' in data
    
    def test_analytics_endpoints(self, client):
        """Test endpoint analytics."""
        response = client.get(
            '/api/v1/analytics/usage/endpoints',
            headers={'Authorization': f'Bearer {client.token}'}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'endpoints' in data
    
    def test_create_api_key(self, client):
        """Test creating an API key."""
        response = client.post(
            '/api/v1/auth/api-keys',
            json={'name': 'Test Key'},
            headers={'Authorization': f'Bearer {client.token}'}
        )
        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'api_key' in data
        assert data['api_key'].startswith('imaginario_live_')
    
    def test_list_api_keys(self, client):
        """Test listing API keys."""
        response = client.get(
            '/api/v1/auth/api-keys',
            headers={'Authorization': f'Bearer {client.token}'}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'api_keys' in data


class TestSearchServiceClient:
    """Tests for SearchServiceClient."""
    
    def test_client_initialization(self):
        """Test client initializes correctly."""
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api-gateway'))
            from app import SearchServiceClient
            
            client = SearchServiceClient('http://localhost:5001', 'test-token')
            assert client.base_url == 'http://localhost:5001'
            assert client.service_token == 'test-token'
        except ImportError:
            pytest.skip("API Gateway dependencies not installed")
    
    @patch('requests.post')
    def test_submit_search(self, mock_post):
        """Test submit search with mocked response."""
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api-gateway'))
            from app import SearchServiceClient
            
            mock_response = MagicMock()
            mock_response.json.return_value = {
                'job_id': 'test-id',
                'status': 'completed',
                'results': []
            }
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            
            client = SearchServiceClient('http://localhost:5001', 'test-token')
            result, status = client.submit_search(1, 'test', [])
            
            assert status == 200
            assert result['job_id'] == 'test-id'
        except ImportError:
            pytest.skip("API Gateway dependencies not installed")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
