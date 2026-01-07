"""
Flask Application - Video Search Platform (Working Monolith)
This is a fully functional monolith application.
Candidates need to break this down into microservices.
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
import os
import jwt
import bcrypt
import uuid
import json
from functools import wraps

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///videos.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET'] = os.getenv('JWT_SECRET', 'your-secret-key-change-in-production')
app.config['JWT_ALGORITHM'] = 'HS256'

db = SQLAlchemy(app)
migrate = Migrate(app, db)
CORS(app)

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
    
    id = db.Column(db.String(36), primary_key=True)  # UUID
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    key_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used_at = db.Column(db.DateTime, nullable=True)

class SearchJob(db.Model):
    __tablename__ = 'search_jobs'
    
    id = db.Column(db.String(36), primary_key=True)  # UUID
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    query = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(20), default='queued')  # queued, processing, completed, failed
    results = db.Column(db.Text)  # JSON string
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

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
        return None
    
    token = auth_header[7:]  # Remove 'Bearer ' prefix
    
    # Try JWT first
    user_id = verify_jwt_token(token)
    if user_id:
        return User.query.get(user_id)
    
    # Try API key
    api_key = APIKey.query.filter_by(is_active=True).all()
    for key in api_key:
        if verify_api_key(token, key.key_hash):
            key.last_used_at = datetime.utcnow()
            db.session.commit()
            return User.query.get(key.user_id)
    
    return None

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_auth_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        kwargs['current_user'] = user
        return f(*args, **kwargs)
    return decorated_function

# ============================================================================
# PLACEHOLDER SEARCH FUNCTION
# ============================================================================

def perform_search(query, video_ids=None):
    """
    Search through videos by title and description.
    
    Args:
        query: Search query string
        video_ids: Optional list of video IDs to search within
    
    Returns:
        List of search results with format:
        [
            {
                'video_id': 1,
                'title': 'Video Title',
                'relevance_score': 0.95,
                'matched_text': 'snippet of matched content'
            }
        ]
    """
    if not query:
        return []
    
    query_lower = query.lower()
    query_words = query_lower.split()
    
    # Build query
    video_query = Video.query
    if video_ids:
        video_query = video_query.filter(Video.id.in_(video_ids))
    
    videos = video_query.all()
    results = []
    
    for video in videos:
        score = 0.0
        matched_parts = []
        
        # Check title matches
        title_lower = video.title.lower() if video.title else ''
        if query_lower in title_lower:
            score += 0.7
            matched_parts.append(video.title)
        else:
            # Check for word matches in title
            for word in query_words:
                if word in title_lower:
                    score += 0.3 / len(query_words)
                    if video.title not in matched_parts:
                        matched_parts.append(video.title)
        
        # Check description matches
        description_lower = (video.description or '').lower()
        if query_lower in description_lower:
            score += 0.3
            # Extract snippet from description
            idx = description_lower.find(query_lower)
            start = max(0, idx - 30)
            end = min(len(description_lower), idx + len(query_lower) + 30)
            snippet = video.description[start:end] if video.description else ''
            if snippet and snippet not in matched_parts:
                matched_parts.append(snippet)
        else:
            # Check for word matches in description
            for word in query_words:
                if word in description_lower:
                    score += 0.1 / len(query_words)
        
        if score > 0:
            results.append({
                'video_id': video.id,
                'title': video.title,
                'relevance_score': min(1.0, score),
                'matched_text': matched_parts[0] if matched_parts else video.title
            })
    
    # Sort by relevance score (descending)
    results.sort(key=lambda x: x['relevance_score'], reverse=True)
    
    return results

# ============================================================================
# AUTH ENDPOINTS (IMPLEMENTED)
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
# VIDEO ENDPOINTS (PARTIALLY IMPLEMENTED - CANDIDATES NEED TO COMPLETE)
# ============================================================================

@app.route('/api/v1/users/<int:user_id>/videos', methods=['GET'])
@require_auth
def list_videos(user_id, current_user):
    """
    List videos for a user.
    
    TODO: Candidates should implement:
    - Pagination (page, per_page query params)
    - Filtering and sorting
    - Return proper video list with metadata
    """
    if user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # TODO: Implement pagination and filtering
    videos = Video.query.filter_by(user_id=user_id).all()
    
    return jsonify({
        'videos': [{
            'id': v.id,
            'title': v.title,
            'description': v.description,
            'duration': v.duration,
            'created_at': v.created_at.isoformat()
        } for v in videos]
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
# SEARCH ENDPOINTS (TODO - CANDIDATES NEED TO IMPLEMENT)
# ============================================================================

@app.route('/api/v1/users/<int:user_id>/search', methods=['POST'])
@require_auth
def submit_search(user_id, current_user):
    """
    Submit a search query.
    
    Request body:
    {
        "query": "search text",
        "video_ids": [1, 2, 3]  // optional, search in specific videos
    }
    
    Response:
    {
        "job_id": "uuid",
        "status": "queued"
    }
    """
    if user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    
    if not data or not data.get('query'):
        return jsonify({'error': 'Query is required'}), 400
    
    # Create search job
    job_id = str(uuid.uuid4())
    search_job = SearchJob(
        id=job_id,
        user_id=user_id,
        query=data['query'],
        status='queued'
    )
    db.session.add(search_job)
    db.session.commit()
    
    # Process search synchronously
    video_ids = data.get('video_ids')
    results = perform_search(data['query'], video_ids)
    
    # Update job with results
    search_job.status = 'completed'
    search_job.results = json.dumps(results)
    search_job.completed_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'job_id': job_id,
        'status': 'completed',
        'results': results
    }), 200

@app.route('/api/v1/users/<int:user_id>/search/<job_id>', methods=['GET'])
@require_auth
def get_search_results(user_id, current_user, job_id):
    """
    Get search job results.
    
    Response:
    {
        "job_id": "uuid",
        "status": "completed",
        "results": [...]
    }
    """
    if user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    search_job = SearchJob.query.filter_by(id=job_id, user_id=user_id).first()
    
    if not search_job:
        return jsonify({'error': 'Search job not found'}), 404
    
    import json
    results = json.loads(search_job.results) if search_job.results else []
    
    return jsonify({
        'job_id': job_id,
        'status': search_job.status,
        'results': results,
        'completed_at': search_job.completed_at.isoformat() if search_job.completed_at else None
    })

# ============================================================================
# API KEY ENDPOINTS (TODO - CANDIDATES NEED TO IMPLEMENT)
# ============================================================================

@app.route('/api/v1/auth/api-keys', methods=['POST'])
@require_auth
def create_api_key(current_user):
    """
    Create a new API key.
    
    Request body:
    {
        "name": "My API Key"
    }
    
    Response:
    {
        "api_key": "imaginario_live_abc123...",
        "api_key_id": "uuid",
        "name": "My API Key",
        "created_at": "..."
    }
    """
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
    """
    List user's API keys.
    
    Returns list of API keys (without the actual key value).
    """
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
    """
    Delete/revoke an API key.
    """
    api_key = APIKey.query.filter_by(id=key_id, user_id=current_user.id).first()
    
    if not api_key:
        return jsonify({'error': 'API key not found'}), 404
    
    db.session.delete(api_key)
    db.session.commit()
    
    return jsonify({'message': 'API key deleted'}), 200

# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'}), 200

# ============================================================================
# INITIALIZATION
# ============================================================================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)

