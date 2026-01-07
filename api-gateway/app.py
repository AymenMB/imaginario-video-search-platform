"""
API Gateway - Flask Application

This is the main API Gateway that:
- Handles all existing endpoints (auth, videos, api-keys)
- Routes search requests to the Search Microservice
- Logs all API requests for analytics
- Provides analytics endpoints for the Developer Dashboard
- Implements Circuit Breaker pattern for resilience
- Provides Swagger/OpenAPI documentation
"""

from flask import Flask, jsonify, request, g
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_socketio import SocketIO, emit, join_room, leave_room
from flasgger import Swagger
from datetime import datetime, timedelta
import os
import jwt
import bcrypt
import uuid
import json
import time
import requests
import threading
from functools import wraps
from enum import Enum

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///videos.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET'] = os.getenv('JWT_SECRET', 'your-secret-key-change-in-production')
app.config['JWT_ALGORITHM'] = 'HS256'
app.config['SEARCH_MICROSERVICE_URL'] = os.getenv('SEARCH_MICROSERVICE_URL', 'http://localhost:5001')
app.config['SERVICE_TOKEN'] = os.getenv('SERVICE_TOKEN', 'service-secret-token-change-in-production')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'websocket-secret-key-change-in-production')

# Swagger configuration
app.config['SWAGGER'] = {
    'title': 'Video Search API',
    'description': 'API Gateway for Video Search Platform with microservices architecture',
    'version': '1.0.0',
    'termsOfService': '',
    'uiversion': 3,
    'specs_route': '/api/docs/'
}
swagger = Swagger(app)

db = SQLAlchemy(app)
migrate = Migrate(app, db)
CORS(app, resources={r"/*": {"origins": "*"}})

# Initialize SocketIO for WebSocket support (real-time notifications)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')



# ============================================================================
# MODELS
# ============================================================================

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    videos = db.relationship('Video', backref='user', lazy=True)
    api_keys = db.relationship('APIKey', backref='user', lazy=True)

class Video(db.Model):
    __tablename__ = 'videos'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    duration = db.Column(db.Integer)  # in seconds
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class APIKey(db.Model):
    __tablename__ = 'api_keys'
    
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    key_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used_at = db.Column(db.DateTime, nullable=True)


class APIRequestLog(db.Model):
    """Log all API requests for analytics."""
    __tablename__ = 'api_request_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    api_key_id = db.Column(db.String(36), nullable=True)
    endpoint = db.Column(db.String(255), nullable=False)
    method = db.Column(db.String(10), nullable=False)
    status_code = db.Column(db.Integer, nullable=False)
    response_time_ms = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    error_message = db.Column(db.Text, nullable=True)


# ============================================================================
# AUTHENTICATION HELPERS
# ============================================================================

def generate_jwt_token(user_id):
    """Generate JWT token for user"""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow().timestamp() + 86400  # 24 hours
    }
    return jwt.encode(payload, app.config['JWT_SECRET'], algorithm=app.config['JWT_ALGORITHM'])

def verify_jwt_token(token):
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def hash_password(password):
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, password_hash):
    """Verify password against hash"""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

def hash_api_key(api_key):
    """Hash API key for storage"""
    return bcrypt.hashpw(api_key.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_api_key(api_key, key_hash):
    """Verify API key against hash"""
    try:
        return bcrypt.checkpw(api_key.encode('utf-8'), key_hash.encode('utf-8'))
    except:
        return False

def get_auth_user():
    """Get authenticated user from JWT or API key"""
    auth_header = request.headers.get('Authorization', '')
    
    if not auth_header.startswith('Bearer '):
        return None, None
    
    token = auth_header[7:]  # Remove 'Bearer ' prefix
    
    # Try JWT first
    user_id = verify_jwt_token(token)
    if user_id:
        return User.query.get(user_id), None
    
    # Try API key
    api_keys = APIKey.query.filter_by(is_active=True).all()
    for key in api_keys:
        if verify_api_key(token, key.key_hash):
            key.last_used_at = datetime.utcnow()
            db.session.commit()
            return User.query.get(key.user_id), key.id
    
    return None, None

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user, api_key_id = get_auth_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        g.current_user = user
        g.api_key_id = api_key_id
        kwargs['current_user'] = user
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# REQUEST LOGGING MIDDLEWARE
# ============================================================================

@app.before_request
def before_request():
    """Store request start time"""
    g.start_time = time.time()

@app.after_request
def after_request(response):
    """Log API request after response"""
    # Skip logging for health check and static files
    if request.path in ['/health', '/favicon.ico']:
        return response
    
    # Calculate response time
    response_time_ms = int((time.time() - getattr(g, 'start_time', time.time())) * 1000)
    
    # Get user info if available
    user_id = getattr(getattr(g, 'current_user', None), 'id', None)
    api_key_id = getattr(g, 'api_key_id', None)
    
    # Log the request
    try:
        log = APIRequestLog(
            user_id=user_id,
            api_key_id=api_key_id,
            endpoint=request.path,
            method=request.method,
            status_code=response.status_code,
            response_time_ms=response_time_ms
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        # Don't fail the request if logging fails
        db.session.rollback()
    
    return response


# ============================================================================
# CIRCUIT BREAKER PATTERN
# ============================================================================

class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """
    Circuit Breaker implementation for resilient microservice communication.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests are rejected immediately
    - HALF_OPEN: Testing if service recovered, allows limited requests
    
    Usage:
        cb = CircuitBreaker(failure_threshold=5, recovery_timeout=30)
        if cb.can_execute():
            try:
                result = make_request()
                cb.record_success()
            except Exception:
                cb.record_failure()
    """
    
    def __init__(self, failure_threshold=5, recovery_timeout=30, half_open_max_calls=3):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.half_open_calls = 0
        self._lock = threading.Lock()
    
    def can_execute(self):
        """Check if a request can be executed."""
        with self._lock:
            if self.state == CircuitBreakerState.CLOSED:
                return True
            
            if self.state == CircuitBreakerState.OPEN:
                # Check if recovery timeout has passed
                if self.last_failure_time and \
                   (time.time() - self.last_failure_time) >= self.recovery_timeout:
                    self.state = CircuitBreakerState.HALF_OPEN
                    self.half_open_calls = 0
                    return True
                return False
            
            if self.state == CircuitBreakerState.HALF_OPEN:
                # Allow limited calls in half-open state
                if self.half_open_calls < self.half_open_max_calls:
                    self.half_open_calls += 1
                    return True
                return False
            
            return False
    
    def record_success(self):
        """Record a successful request."""
        with self._lock:
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.half_open_max_calls:
                    # Recovery confirmed, close the circuit
                    self.state = CircuitBreakerState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
            elif self.state == CircuitBreakerState.CLOSED:
                self.failure_count = 0  # Reset on success
    
    def record_failure(self):
        """Record a failed request."""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.state == CircuitBreakerState.HALF_OPEN:
                # Failure in half-open, back to open
                self.state = CircuitBreakerState.OPEN
                self.success_count = 0
            elif self.state == CircuitBreakerState.CLOSED:
                if self.failure_count >= self.failure_threshold:
                    self.state = CircuitBreakerState.OPEN
    
    def get_state(self):
        """Get current circuit breaker state info."""
        with self._lock:
            return {
                'state': self.state.value,
                'failure_count': self.failure_count,
                'failure_threshold': self.failure_threshold,
                'recovery_timeout': self.recovery_timeout,
                'last_failure_time': self.last_failure_time
            }


# Global circuit breaker for search service
search_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=30,
    half_open_max_calls=3
)


# ============================================================================
# SEARCH MICROSERVICE CLIENT
# ============================================================================

class SearchServiceClient:
    """
    Client for communicating with the Search Microservice.
    Integrates with Circuit Breaker for resilient communication.
    """
    
    def __init__(self, base_url, service_token, circuit_breaker=None):
        self.base_url = base_url.rstrip('/')
        self.service_token = service_token
        self.timeout = 30  # seconds
        self.circuit_breaker = circuit_breaker
    
    def _headers(self):
        return {
            'Content-Type': 'application/json',
            'X-Service-Token': self.service_token
        }
    
    def _make_request(self, method, url, **kwargs):
        """Make a request with circuit breaker protection."""
        # Check circuit breaker
        if self.circuit_breaker and not self.circuit_breaker.can_execute():
            return {'error': 'Search service circuit breaker is open', 'circuit_breaker': 'open'}, 503
        
        try:
            response = getattr(requests, method)(url, **kwargs)
            
            # Record success
            if self.circuit_breaker and response.status_code < 500:
                self.circuit_breaker.record_success()
            elif self.circuit_breaker:
                self.circuit_breaker.record_failure()
                
            return response.json(), response.status_code
            
        except requests.exceptions.ConnectionError:
            if self.circuit_breaker:
                self.circuit_breaker.record_failure()
            return {'error': 'Search service unavailable'}, 503
        except requests.exceptions.Timeout:
            if self.circuit_breaker:
                self.circuit_breaker.record_failure()
            return {'error': 'Search service timeout'}, 504
        except Exception as e:
            if self.circuit_breaker:
                self.circuit_breaker.record_failure()
            return {'error': str(e)}, 500
    
    def submit_search(self, user_id, query, videos, algorithm='text_search'):
        """Submit a search job to the microservice."""
        return self._make_request(
            'post',
            f"{self.base_url}/api/v1/search/jobs",
            headers=self._headers(),
            json={
                'user_id': user_id,
                'query': query,
                'videos': videos,
                'algorithm': algorithm
            },
            timeout=self.timeout
        )
    
    def get_search_job(self, job_id):
        """Get search job results."""
        return self._make_request(
            'get',
            f"{self.base_url}/api/v1/search/jobs/{job_id}",
            headers=self._headers(),
            timeout=self.timeout
        )
    
    def list_search_jobs(self, user_id, **filters):
        """List search jobs for a user."""
        params = {'user_id': user_id, **filters}
        return self._make_request(
            'get',
            f"{self.base_url}/api/v1/search/jobs",
            headers=self._headers(),
            params=params,
            timeout=self.timeout
        )
    
    def get_job_details(self, job_id):
        """Get detailed job information."""
        return self._make_request(
            'get',
            f"{self.base_url}/api/v1/search/jobs/{job_id}/details",
            headers=self._headers(),
            timeout=self.timeout
        )
    
    def retry_job(self, job_id):
        """Retry a failed or completed search job."""
        return self._make_request(
            'post',
            f"{self.base_url}/api/v1/search/jobs/{job_id}/retry",
            headers=self._headers(),
            timeout=self.timeout
        )
    
    def cancel_job(self, job_id):
        """Cancel a queued or processing search job."""
        return self._make_request(
            'post',
            f"{self.base_url}/api/v1/search/jobs/{job_id}/cancel",
            headers=self._headers(),
            timeout=self.timeout
        )
    
    def health_check(self):
        """Check if search service is healthy."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False


# Create search service client with circuit breaker
search_client = SearchServiceClient(
    app.config['SEARCH_MICROSERVICE_URL'],
    app.config['SERVICE_TOKEN'],
    circuit_breaker=search_circuit_breaker
)



# ============================================================================
# AUTH ENDPOINTS
# ============================================================================

@app.route('/api/v1/auth/register', methods=['POST'])
def register():
    """Register a new user"""
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password required'}), 400
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 400
    
    user = User(
        email=data['email'],
        name=data.get('name', ''),
        password_hash=hash_password(data['password'])
    )
    db.session.add(user)
    db.session.commit()
    
    token = generate_jwt_token(user.id)
    
    return jsonify({
        'user': {
            'id': user.id,
            'email': user.email,
            'name': user.name
        },
        'token': token
    }), 201

@app.route('/api/v1/auth/login', methods=['POST'])
def login():
    """Login user and return JWT token"""
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password required'}), 400
    
    user = User.query.filter_by(email=data['email']).first()
    
    if not user or not verify_password(data['password'], user.password_hash):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    token = generate_jwt_token(user.id)
    
    return jsonify({
        'user': {
            'id': user.id,
            'email': user.email,
            'name': user.name
        },
        'token': token
    })


# ============================================================================
# VIDEO ENDPOINTS
# ============================================================================

@app.route('/api/v1/users/<int:user_id>/videos', methods=['GET'])
@require_auth
def list_videos(user_id, current_user):
    """List videos for a user."""
    if user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = Video.query.filter_by(user_id=user_id).order_by(Video.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'videos': [{
            'id': v.id,
            'title': v.title,
            'description': v.description,
            'duration': v.duration,
            'created_at': v.created_at.isoformat()
        } for v in pagination.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total_pages': pagination.pages,
            'total_items': pagination.total
        }
    })

@app.route('/api/v1/users/<int:user_id>/videos', methods=['POST'])
@require_auth
def create_video(user_id, current_user):
    """Create a new video"""
    if user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    
    if not data or not data.get('title'):
        return jsonify({'error': 'Title is required'}), 400
    
    video = Video(
        user_id=user_id,
        title=data['title'],
        description=data.get('description', ''),
        duration=data.get('duration', 0)
    )
    db.session.add(video)
    db.session.commit()
    
    return jsonify({
        'id': video.id,
        'title': video.title,
        'description': video.description,
        'duration': video.duration,
        'created_at': video.created_at.isoformat()
    }), 201

@app.route('/api/v1/users/<int:user_id>/videos/<int:video_id>', methods=['GET'])
@require_auth
def get_video(user_id, current_user, video_id):
    """Get video details"""
    if user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    video = Video.query.filter_by(id=video_id, user_id=user_id).first()
    
    if not video:
        return jsonify({'error': 'Video not found'}), 404
    
    return jsonify({
        'id': video.id,
        'title': video.title,
        'description': video.description,
        'duration': video.duration,
        'created_at': video.created_at.isoformat()
    })

@app.route('/api/v1/users/<int:user_id>/videos/<int:video_id>', methods=['PUT'])
@require_auth
def update_video(user_id, current_user, video_id):
    """Update video"""
    if user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    video = Video.query.filter_by(id=video_id, user_id=user_id).first()
    
    if not video:
        return jsonify({'error': 'Video not found'}), 404
    
    data = request.get_json()
    
    if data.get('title'):
        video.title = data['title']
    if data.get('description') is not None:
        video.description = data['description']
    if data.get('duration') is not None:
        video.duration = data['duration']
    
    video.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'id': video.id,
        'title': video.title,
        'description': video.description,
        'duration': video.duration,
        'updated_at': video.updated_at.isoformat()
    })

@app.route('/api/v1/users/<int:user_id>/videos/<int:video_id>', methods=['DELETE'])
@require_auth
def delete_video(user_id, current_user, video_id):
    """Delete video"""
    if user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    video = Video.query.filter_by(id=video_id, user_id=user_id).first()
    
    if not video:
        return jsonify({'error': 'Video not found'}), 404
    
    db.session.delete(video)
    db.session.commit()
    
    return jsonify({'message': 'Video deleted'}), 200


# ============================================================================
# SEARCH ENDPOINTS (Routed to Search Microservice)
# ============================================================================

@app.route('/api/v1/users/<int:user_id>/search', methods=['POST'])
@require_auth
def submit_search(user_id, current_user):
    """
    Submit a search query.
    Routes to Search Microservice.
    """
    if user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    
    if not data or not data.get('query'):
        return jsonify({'error': 'Query is required'}), 400
    
    # Get videos for the user
    video_ids = data.get('video_ids')
    if video_ids:
        videos = Video.query.filter(
            Video.user_id == user_id,
            Video.id.in_(video_ids)
        ).all()
    else:
        videos = Video.query.filter_by(user_id=user_id).all()
    
    # Convert to dict for microservice
    videos_data = [{
        'id': v.id,
        'title': v.title,
        'description': v.description
    } for v in videos]
    
    # Call search microservice
    algorithm = data.get('algorithm', 'text_search')
    result, status_code = search_client.submit_search(
        user_id=user_id,
        query=data['query'],
        videos=videos_data,
        algorithm=algorithm
    )
    
    return jsonify(result), status_code

@app.route('/api/v1/users/<int:user_id>/search/<job_id>', methods=['GET'])
@require_auth
def get_search_results(user_id, current_user, job_id):
    """
    Get search job results.
    Routes to Search Microservice.
    """
    if user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    result, status_code = search_client.get_search_job(job_id)
    return jsonify(result), status_code


# ============================================================================
# API KEY ENDPOINTS
# ============================================================================

@app.route('/api/v1/auth/api-keys', methods=['POST'])
@require_auth
def create_api_key(current_user):
    """Create a new API key."""
    data = request.get_json()
    
    if not data or not data.get('name'):
        return jsonify({'error': 'Name is required'}), 400
    
    # Generate API key
    key_uuid = str(uuid.uuid4())
    api_key = f"imaginario_live_{key_uuid}"
    
    # Hash and store
    key_id = str(uuid.uuid4())
    api_key_record = APIKey(
        id=key_id,
        user_id=current_user.id,
        name=data['name'],
        key_hash=hash_api_key(api_key),
        is_active=True
    )
    db.session.add(api_key_record)
    db.session.commit()
    
    return jsonify({
        'api_key': api_key,  # Only shown once
        'api_key_id': key_id,
        'name': data['name'],
        'created_at': api_key_record.created_at.isoformat()
    }), 201

@app.route('/api/v1/auth/api-keys', methods=['GET'])
@require_auth
def list_api_keys(current_user):
    """List user's API keys."""
    api_keys = APIKey.query.filter_by(user_id=current_user.id).all()
    
    return jsonify({
        'api_keys': [{
            'id': key.id,
            'name': key.name,
            'is_active': key.is_active,
            'created_at': key.created_at.isoformat(),
            'last_used_at': key.last_used_at.isoformat() if key.last_used_at else None
        } for key in api_keys]
    })

@app.route('/api/v1/auth/api-keys/<key_id>', methods=['DELETE'])
@require_auth
def delete_api_key(current_user, key_id):
    """Delete/revoke an API key."""
    api_key = APIKey.query.filter_by(id=key_id, user_id=current_user.id).first()
    
    if not api_key:
        return jsonify({'error': 'API key not found'}), 404
    
    db.session.delete(api_key)
    db.session.commit()
    
    return jsonify({'message': 'API key deleted'}), 200


# ============================================================================
# ANALYTICS ENDPOINTS (For Developer Dashboard)
# ============================================================================

@app.route('/api/v1/analytics/usage', methods=['GET'])
@require_auth
def get_usage_stats(current_user):
    """
    Get API usage statistics.
    
    Query params:
    - start_date: ISO date (default: 30 days ago)
    - end_date: ISO date (default: now)
    - api_key_id: Optional filter by API key
    """
    # Parse date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)
    
    if request.args.get('start_date'):
        try:
            start_date = datetime.fromisoformat(request.args.get('start_date').replace('Z', '+00:00'))
        except:
            pass
    
    if request.args.get('end_date'):
        try:
            end_date = datetime.fromisoformat(request.args.get('end_date').replace('Z', '+00:00'))
        except:
            pass
    
    # Build query
    query = APIRequestLog.query.filter(
        APIRequestLog.user_id == current_user.id,
        APIRequestLog.timestamp >= start_date,
        APIRequestLog.timestamp <= end_date
    )
    
    api_key_id = request.args.get('api_key_id')
    if api_key_id:
        query = query.filter(APIRequestLog.api_key_id == api_key_id)
    
    logs = query.all()
    
    # Calculate statistics
    total_requests = len(logs)
    successful = sum(1 for l in logs if 200 <= l.status_code < 400)
    errors = sum(1 for l in logs if l.status_code >= 400)
    
    response_times = [l.response_time_ms for l in logs]
    avg_response_time = sum(response_times) / len(response_times) if response_times else 0
    
    # Sort for percentiles
    response_times.sort()
    p95 = response_times[int(len(response_times) * 0.95)] if response_times else 0
    p99 = response_times[int(len(response_times) * 0.99)] if response_times else 0
    
    # Group by endpoint
    endpoint_stats = {}
    for log in logs:
        if log.endpoint not in endpoint_stats:
            endpoint_stats[log.endpoint] = {'count': 0, 'errors': 0}
        endpoint_stats[log.endpoint]['count'] += 1
        if log.status_code >= 400:
            endpoint_stats[log.endpoint]['errors'] += 1
    
    return jsonify({
        'period': {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat()
        },
        'summary': {
            'total_requests': total_requests,
            'successful_requests': successful,
            'error_requests': errors,
            'error_rate': (errors / total_requests * 100) if total_requests > 0 else 0,
            'avg_response_time_ms': round(avg_response_time, 2),
            'p95_response_time_ms': p95,
            'p99_response_time_ms': p99
        },
        'endpoints': endpoint_stats
    })

@app.route('/api/v1/analytics/usage/daily', methods=['GET'])
@require_auth
def get_daily_usage(current_user):
    """Get daily usage breakdown for charts."""
    # Last 30 days by default
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)
    
    if request.args.get('start_date'):
        try:
            start_date = datetime.fromisoformat(request.args.get('start_date').replace('Z', '+00:00'))
        except:
            pass
    
    if request.args.get('end_date'):
        try:
            end_date = datetime.fromisoformat(request.args.get('end_date').replace('Z', '+00:00'))
        except:
            pass
    
    # Build query
    query = APIRequestLog.query.filter(
        APIRequestLog.user_id == current_user.id,
        APIRequestLog.timestamp >= start_date,
        APIRequestLog.timestamp <= end_date
    )
    
    api_key_id = request.args.get('api_key_id')
    if api_key_id:
        query = query.filter(APIRequestLog.api_key_id == api_key_id)
    
    logs = query.all()
    
    # Group by day
    daily_stats = {}
    for log in logs:
        day = log.timestamp.strftime('%Y-%m-%d')
        if day not in daily_stats:
            daily_stats[day] = {
                'date': day,
                'total': 0,
                'successful': 0,
                'errors': 0,
                'avg_response_time_ms': 0,
                'response_times': []
            }
        daily_stats[day]['total'] += 1
        daily_stats[day]['response_times'].append(log.response_time_ms)
        if 200 <= log.status_code < 400:
            daily_stats[day]['successful'] += 1
        else:
            daily_stats[day]['errors'] += 1
    
    # Calculate averages and remove temp data
    result = []
    for day in sorted(daily_stats.keys()):
        stats = daily_stats[day]
        stats['avg_response_time_ms'] = round(
            sum(stats['response_times']) / len(stats['response_times']), 2
        ) if stats['response_times'] else 0
        del stats['response_times']
        result.append(stats)
    
    return jsonify({'daily': result})

@app.route('/api/v1/analytics/usage/endpoints', methods=['GET'])
@require_auth
def get_endpoint_usage(current_user):
    """Get usage breakdown by endpoint for charts."""
    # Last 30 days by default
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)
    
    query = APIRequestLog.query.filter(
        APIRequestLog.user_id == current_user.id,
        APIRequestLog.timestamp >= start_date,
        APIRequestLog.timestamp <= end_date
    )
    
    logs = query.all()
    
    # Group by endpoint
    endpoint_stats = {}
    for log in logs:
        # Simplify endpoint names
        endpoint = log.endpoint
        if endpoint not in endpoint_stats:
            endpoint_stats[endpoint] = {
                'endpoint': endpoint,
                'method': log.method,
                'total': 0,
                'successful': 0,
                'errors': 0,
                'avg_response_time_ms': 0,
                'response_times': []
            }
        endpoint_stats[endpoint]['total'] += 1
        endpoint_stats[endpoint]['response_times'].append(log.response_time_ms)
        if 200 <= log.status_code < 400:
            endpoint_stats[endpoint]['successful'] += 1
        else:
            endpoint_stats[endpoint]['errors'] += 1
    
    # Calculate averages
    result = []
    for endpoint, stats in endpoint_stats.items():
        stats['avg_response_time_ms'] = round(
            sum(stats['response_times']) / len(stats['response_times']), 2
        ) if stats['response_times'] else 0
        del stats['response_times']
        result.append(stats)
    
    # Sort by total requests
    result.sort(key=lambda x: x['total'], reverse=True)
    
    return jsonify({'endpoints': result})


@app.route('/api/v1/auth/api-keys/<key_id>/usage', methods=['GET'])
@require_auth
def get_api_key_usage(current_user, key_id):
    """Get usage statistics for a specific API key."""
    # Verify key belongs to user
    api_key = APIKey.query.filter_by(id=key_id, user_id=current_user.id).first()
    if not api_key:
        return jsonify({'error': 'API key not found'}), 404
    
    # Last 30 days
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)
    
    logs = APIRequestLog.query.filter(
        APIRequestLog.api_key_id == key_id,
        APIRequestLog.timestamp >= start_date,
        APIRequestLog.timestamp <= end_date
    ).all()
    
    total_requests = len(logs)
    successful = sum(1 for l in logs if 200 <= l.status_code < 400)
    errors = sum(1 for l in logs if l.status_code >= 400)
    
    response_times = [l.response_time_ms for l in logs]
    avg_response_time = sum(response_times) / len(response_times) if response_times else 0
    
    return jsonify({
        'api_key': {
            'id': api_key.id,
            'name': api_key.name,
            'is_active': api_key.is_active,
            'created_at': api_key.created_at.isoformat(),
            'last_used_at': api_key.last_used_at.isoformat() if api_key.last_used_at else None
        },
        'usage': {
            'total_requests': total_requests,
            'successful_requests': successful,
            'error_requests': errors,
            'error_rate': (errors / total_requests * 100) if total_requests > 0 else 0,
            'avg_response_time_ms': round(avg_response_time, 2)
        }
    })


@app.route('/api/v1/auth/api-keys/<key_id>/usage/daily', methods=['GET'])
@require_auth
def get_api_key_daily_usage(current_user, key_id):
    """Get daily usage for a specific API key."""
    # Verify key belongs to user
    api_key = APIKey.query.filter_by(id=key_id, user_id=current_user.id).first()
    if not api_key:
        return jsonify({'error': 'API key not found'}), 404
    
    # Last 30 days
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)
    
    logs = APIRequestLog.query.filter(
        APIRequestLog.api_key_id == key_id,
        APIRequestLog.timestamp >= start_date,
        APIRequestLog.timestamp <= end_date
    ).all()
    
    # Group by day
    daily_stats = {}
    for log in logs:
        day = log.timestamp.strftime('%Y-%m-%d')
        if day not in daily_stats:
            daily_stats[day] = {'date': day, 'total': 0, 'errors': 0}
        daily_stats[day]['total'] += 1
        if log.status_code >= 400:
            daily_stats[day]['errors'] += 1
    
    result = [daily_stats[day] for day in sorted(daily_stats.keys())]
    
    return jsonify({'daily': result})


# ============================================================================
# SEARCH JOBS ENDPOINTS (For Developer Dashboard)
# ============================================================================

@app.route('/api/v1/search/jobs', methods=['GET'])
@require_auth
def list_search_jobs(current_user):
    """
    List all search jobs for the current user.
    Routes to Search Microservice.
    """
    # Build filters from query params
    filters = {}
    
    if request.args.get('status'):
        filters['status'] = request.args.get('status')
    if request.args.get('start_date'):
        filters['start_date'] = request.args.get('start_date')
    if request.args.get('end_date'):
        filters['end_date'] = request.args.get('end_date')
    if request.args.get('page'):
        filters['page'] = request.args.get('page', 1, type=int)
    if request.args.get('per_page'):
        filters['per_page'] = request.args.get('per_page', 20, type=int)
    
    # Pass the current user's ID to the search microservice
    result, status_code = search_client.list_search_jobs(current_user.id, **filters)
    return jsonify(result), status_code

@app.route('/api/v1/search/jobs/<job_id>/details', methods=['GET'])
@require_auth
def get_search_job_details(current_user, job_id):
    """
    Get detailed search job information.
    Routes to Search Microservice.
    """
    result, status_code = search_client.get_job_details(job_id)
    return jsonify(result), status_code


@app.route('/api/v1/search/jobs/<job_id>/retry', methods=['POST'])
@require_auth
def retry_search_job(current_user, job_id):
    """
    Retry a failed or completed search job.
    Creates a new job with the same parameters.
    ---
    tags:
      - Search Jobs
    parameters:
      - name: job_id
        in: path
        type: string
        required: true
    responses:
      201:
        description: Job retry initiated
      404:
        description: Job not found
    """
    result, status_code = search_client.retry_job(job_id)
    return jsonify(result), status_code


@app.route('/api/v1/search/jobs/<job_id>/cancel', methods=['POST'])
@require_auth
def cancel_search_job(current_user, job_id):
    """
    Cancel a queued or processing search job.
    ---
    tags:
      - Search Jobs
    parameters:
      - name: job_id
        in: path
        type: string
        required: true
    responses:
      200:
        description: Job cancelled successfully
      400:
        description: Cannot cancel job with current status
      404:
        description: Job not found
    """
    result, status_code = search_client.cancel_job(job_id)
    return jsonify(result), status_code


# ============================================================================
# CIRCUIT BREAKER STATUS
# ============================================================================

@app.route('/api/v1/system/circuit-breaker', methods=['GET'])
@require_auth
def get_circuit_breaker_status(current_user):
    """
    Get circuit breaker status for monitoring.
    ---
    tags:
      - System
    responses:
      200:
        description: Circuit breaker status
    """
    return jsonify({
        'search_service': search_circuit_breaker.get_state()
    }), 200


# ============================================================================
# WEBSOCKET EVENTS (Real-time Notifications)
# ============================================================================

# Store active connections by user_id
connected_users = {}

@socketio.on('connect')
def handle_connect():
    """Handle client WebSocket connection."""
    print(f"Client connected: {request.sid}")
    emit('connected', {'message': 'Connected to WebSocket server', 'sid': request.sid})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client WebSocket disconnection."""
    # Remove from connected users if present
    for user_id, sid in list(connected_users.items()):
        if sid == request.sid:
            del connected_users[user_id]
            print(f"User {user_id} disconnected")
            break
    print(f"Client disconnected: {request.sid}")

@socketio.on('authenticate')
def handle_authenticate(data):
    """
    Authenticate WebSocket connection with JWT token.
    After authentication, user will receive real-time job notifications.
    """
    token = data.get('token')
    if not token:
        emit('auth_error', {'error': 'Token required'})
        return
    
    try:
        payload = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        user_id = payload['user_id']
        connected_users[user_id] = request.sid
        join_room(f'user_{user_id}')
        emit('authenticated', {'message': 'Authenticated successfully', 'user_id': user_id})
        print(f"User {user_id} authenticated on WebSocket")
    except jwt.ExpiredSignatureError:
        emit('auth_error', {'error': 'Token expired'})
    except jwt.InvalidTokenError:
        emit('auth_error', {'error': 'Invalid token'})

@socketio.on('subscribe_jobs')
def handle_subscribe_jobs(data):
    """Subscribe to job status updates."""
    user_id = data.get('user_id')
    if user_id:
        join_room(f'jobs_{user_id}')
        emit('subscribed', {'message': f'Subscribed to job updates', 'room': f'jobs_{user_id}'})

@socketio.on('unsubscribe_jobs')
def handle_unsubscribe_jobs(data):
    """Unsubscribe from job status updates."""
    user_id = data.get('user_id')
    if user_id:
        leave_room(f'jobs_{user_id}')
        emit('unsubscribed', {'message': f'Unsubscribed from job updates'})

def notify_job_status_change(user_id, job_id, status, message=None):
    """
    Send real-time notification when job status changes.
    Called from search endpoints when job status updates.
    """
    notification = {
        'type': 'job_status_update',
        'job_id': job_id,
        'status': status,
        'message': message or f'Job {job_id} is now {status}',
        'timestamp': datetime.utcnow().isoformat()
    }
    # Emit to user's job room
    socketio.emit('job_update', notification, room=f'jobs_{user_id}')
    # Also emit to user's personal room
    socketio.emit('notification', notification, room=f'user_{user_id}')

def notify_analytics_update(user_id):
    """Send notification when analytics data is updated."""
    notification = {
        'type': 'analytics_update',
        'message': 'New analytics data available',
        'timestamp': datetime.utcnow().isoformat()
    }
    socketio.emit('analytics_update', notification, room=f'user_{user_id}')


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.route('/health', methods=['GET'])
def health():
    """
    Health check endpoint.
    ---
    tags:
      - System
    responses:
      200:
        description: Service health status
    """
    search_healthy = search_client.health_check()
    circuit_state = search_circuit_breaker.get_state()
    
    return jsonify({
        'status': 'healthy',
        'service': 'api-gateway',
        'timestamp': datetime.utcnow().isoformat(),
        'dependencies': {
            'search_microservice': 'healthy' if search_healthy else 'unavailable'
        },
        'circuit_breaker': {
            'search_service': circuit_state['state']
        },
        'websocket': {
            'enabled': True,
            'connected_users': len(connected_users)
        }
    }), 200


# ============================================================================
# INITIALIZATION
# ============================================================================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    # Use socketio.run instead of app.run for WebSocket support
    # Bind to 0.0.0.0 for Docker container access
    socketio.run(app, debug=True, port=5000, host='0.0.0.0', allow_unsafe_werkzeug=True)
