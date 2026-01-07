"""
Search Microservice - Flask Application

This microservice handles all search-related operations.
It receives search requests from the API Gateway and processes them
using extensible search algorithms.
"""

from flask import Flask, jsonify, request, g
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import uuid
import json
import time
from functools import wraps

from search_algorithms import SearchAlgorithmFactory

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///search_jobs.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SERVICE_TOKEN'] = os.getenv('SERVICE_TOKEN', 'service-secret-token-change-in-production')

db = SQLAlchemy(app)
CORS(app)

# ============================================================================
# MODELS
# ============================================================================

class SearchJob(db.Model):
    """Search job model for the search microservice."""
    __tablename__ = 'search_jobs'
    
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    search_query = db.Column(db.String(500), nullable=False)  # Renamed from 'query' to avoid SQLAlchemy conflict
    algorithm = db.Column(db.String(50), default='text_search')
    status = db.Column(db.String(20), default='queued')  # queued, processing, completed, failed
    results = db.Column(db.Text)  # JSON string
    results_count = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text, nullable=True)
    execution_time_ms = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    def to_dict(self, include_results=True):
        """Convert to dictionary."""
        data = {
            'job_id': self.id,
            'user_id': self.user_id,
            'query': self.search_query,  # Return as 'query' for API compatibility
            'algorithm': self.algorithm,
            'status': self.status,
            'results_count': self.results_count,
            'execution_time_ms': self.execution_time_ms,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }
        if include_results and self.results:
            data['results'] = json.loads(self.results)
        if self.error_message:
            data['error_message'] = self.error_message
        return data


# ============================================================================
# AUTHENTICATION
# ============================================================================

def require_service_auth(f):
    """Require service-to-service authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('X-Service-Token', '')
        if token != app.config['SERVICE_TOKEN']:
            return jsonify({'error': 'Invalid service token'}), 401
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'search-microservice',
        'timestamp': datetime.utcnow().isoformat(),
        'algorithms': SearchAlgorithmFactory.list_algorithms()
    }), 200


@app.route('/api/v1/search/algorithms', methods=['GET'])
def list_algorithms():
    """List available search algorithms."""
    return jsonify({
        'algorithms': SearchAlgorithmFactory.list_algorithms()
    }), 200


@app.route('/api/v1/search/jobs', methods=['POST'])
@require_service_auth
def submit_search_job():
    """
    Submit a new search job.
    
    Request body:
    {
        "user_id": 1,
        "query": "search text",
        "videos": [{"id": 1, "title": "...", "description": "..."}],
        "algorithm": "text_search"  // optional
    }
    
    Response:
    {
        "job_id": "uuid",
        "status": "completed",
        "results": [...]
    }
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Request body required'}), 400
    
    if not data.get('user_id'):
        return jsonify({'error': 'user_id is required'}), 400
    
    if not data.get('query'):
        return jsonify({'error': 'query is required'}), 400
    
    if not data.get('videos'):
        return jsonify({'error': 'videos list is required'}), 400
    
    # Create search job
    job_id = str(uuid.uuid4())
    algorithm_name = data.get('algorithm', 'text_search')
    
    search_job = SearchJob(
        id=job_id,
        user_id=data['user_id'],
        search_query=data['query'],  # Use search_query field
        algorithm=algorithm_name,
        status='processing',
        started_at=datetime.utcnow()
    )
    db.session.add(search_job)
    db.session.commit()
    
    try:
        # Process search
        start_time = time.time()
        
        algorithm = SearchAlgorithmFactory.get_algorithm(algorithm_name)
        results = algorithm.search(data['query'], data['videos'])
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Update job with results
        search_job.status = 'completed'
        search_job.results = json.dumps(results)
        search_job.results_count = len(results)
        search_job.execution_time_ms = execution_time_ms
        search_job.completed_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'job_id': job_id,
            'status': 'completed',
            'results': results,
            'results_count': len(results),
            'execution_time_ms': execution_time_ms
        }), 200
        
    except Exception as e:
        search_job.status = 'failed'
        search_job.error_message = str(e)
        search_job.completed_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'job_id': job_id,
            'status': 'failed',
            'error': str(e)
        }), 500


@app.route('/api/v1/search/jobs/<job_id>', methods=['GET'])
@require_service_auth
def get_search_job(job_id):
    """
    Get search job results.
    
    Response:
    {
        "job_id": "uuid",
        "status": "completed",
        "results": [...],
        "execution_time_ms": 45
    }
    """
    search_job = SearchJob.query.get(job_id)
    
    if not search_job:
        return jsonify({'error': 'Search job not found'}), 404
    
    return jsonify(search_job.to_dict()), 200


@app.route('/api/v1/search/jobs', methods=['GET'])
@require_service_auth
def list_search_jobs():
    """
    List search jobs for a user.
    
    Query params:
    - user_id: Required
    - status: Optional filter by status
    - start_date: Optional ISO date
    - end_date: Optional ISO date
    - page: Page number (default 1)
    - per_page: Items per page (default 20, max 100)
    """
    user_id = request.args.get('user_id', type=int)
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400
    
    # Build query
    query = SearchJob.query.filter_by(user_id=user_id)
    
    # Optional filters
    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)
    
    start_date = request.args.get('start_date')
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.filter(SearchJob.created_at >= start_dt)
        except:
            pass
    
    end_date = request.args.get('end_date')
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.filter(SearchJob.created_at <= end_dt)
        except:
            pass
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    
    # Order by most recent first
    query = query.order_by(SearchJob.created_at.desc())
    
    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'jobs': [job.to_dict(include_results=False) for job in pagination.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total_pages': pagination.pages,
            'total_items': pagination.total,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }
    }), 200


@app.route('/api/v1/search/jobs/<job_id>/details', methods=['GET'])
@require_service_auth
def get_search_job_details(job_id):
    """
    Get detailed search job information including full results.
    """
    search_job = SearchJob.query.get(job_id)
    
    if not search_job:
        return jsonify({'error': 'Search job not found'}), 404
    
    data = search_job.to_dict(include_results=True)
    
    # Add additional details
    if search_job.results:
        results = json.loads(search_job.results)
        if results:
            data['top_result'] = results[0] if results else None
            data['avg_relevance'] = sum(r['relevance_score'] for r in results) / len(results) if results else 0
    
    return jsonify(data), 200


@app.route('/api/v1/search/jobs/<job_id>/retry', methods=['POST'])
@require_service_auth
def retry_search_job(job_id):
    """
    Retry a failed or completed search job.
    Creates a new job with the same parameters.
    """
    original_job = SearchJob.query.get(job_id)
    
    if not original_job:
        return jsonify({'error': 'Search job not found'}), 404
    
    # Create new job based on original
    new_job_id = str(uuid.uuid4())
    
    new_job = SearchJob(
        id=new_job_id,
        user_id=original_job.user_id,
        search_query=original_job.search_query,
        algorithm=original_job.algorithm,
        status='queued',
        created_at=datetime.utcnow()
    )
    db.session.add(new_job)
    db.session.commit()
    
    return jsonify({
        'message': 'Job retry initiated',
        'original_job_id': job_id,
        'new_job_id': new_job_id,
        'status': 'queued'
    }), 201


@app.route('/api/v1/search/jobs/<job_id>/cancel', methods=['POST'])
@require_service_auth
def cancel_search_job(job_id):
    """
    Cancel a queued or processing search job.
    """
    search_job = SearchJob.query.get(job_id)
    
    if not search_job:
        return jsonify({'error': 'Search job not found'}), 404
    
    if search_job.status in ['completed', 'failed', 'cancelled']:
        return jsonify({
            'error': f'Cannot cancel job with status: {search_job.status}'
        }), 400
    
    search_job.status = 'cancelled'
    search_job.completed_at = datetime.utcnow()
    search_job.error_message = 'Cancelled by user'
    db.session.commit()
    
    return jsonify({
        'message': 'Job cancelled successfully',
        'job_id': job_id,
        'status': 'cancelled'
    }), 200


# ============================================================================
# INITIALIZATION
# ============================================================================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    port = int(os.getenv('PORT', 5001))
    app.run(debug=True, port=port, host='0.0.0.0')

