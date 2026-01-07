# Video Search Platform - Backend Starter

This is a starter Flask backend application. Candidates need to complete the TODO items marked in the code.

## Setup

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set environment variables:
```bash
cp .env.example .env
# Edit .env with your values
```

4. Initialize database:
```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

Or if using SQLite, the database will be created automatically on first run.

5. Run the server:
```bash
python app.py
```

The API will be available at `http://localhost:5000`

## API Endpoints

### Implemented
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login (returns JWT)
- `GET /api/v1/users/<user_id>/videos` - List videos (basic implementation)
- `POST /api/v1/users/<user_id>/videos` - Create video
- `GET /api/v1/users/<user_id>/videos/<video_id>` - Get video
- `PUT /api/v1/users/<user_id>/videos/<video_id>` - Update video
- `DELETE /api/v1/users/<user_id>/videos/<video_id>` - Delete video

### TODO - Candidates Need to Implement
- `POST /api/v1/users/<user_id>/search` - Submit search query
- `GET /api/v1/users/<user_id>/search/<job_id>` - Get search results
- `POST /api/v1/auth/api-keys` - Create API key
- `GET /api/v1/auth/api-keys` - List API keys
- `DELETE /api/v1/auth/api-keys/<key_id>` - Delete API key

## Authentication

The API supports two authentication methods:
1. **JWT Tokens**: Use `Bearer <jwt_token>` in Authorization header
2. **API Keys**: Use `Bearer <api_key>` in Authorization header (once implemented)

## Database Models

- `User`: User accounts
- `Video`: Video metadata
- `APIKey`: API keys for programmatic access
- `SearchJob`: Search job tracking

## Search Function

There's a placeholder `perform_search()` function in `app.py` that candidates need to implement. It should:
- Search through video titles and descriptions
- Return results with relevance scores
- Support filtering by video_ids

