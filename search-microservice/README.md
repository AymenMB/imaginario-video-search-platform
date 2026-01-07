# Search Microservice

Flask-based microservice for handling search operations.

## Features

- Extensible search algorithms (Strategy Pattern)
- Service-to-service authentication
- Search job tracking with execution metrics
- RESTful API

## Setup

```bash
cd search-microservice
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection string | `sqlite:///search_jobs.db` |
| `SERVICE_TOKEN` | Service-to-service auth token | `service-secret-token-change-in-production` |
| `PORT` | Port to run on | `5001` |

## Running

```bash
python app.py
```

Service runs on `http://localhost:5001`

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/api/v1/search/algorithms` | List available algorithms |
| `POST` | `/api/v1/search/jobs` | Submit search job |
| `GET` | `/api/v1/search/jobs/<job_id>` | Get job results |
| `GET` | `/api/v1/search/jobs` | List jobs (with filters) |
| `GET` | `/api/v1/search/jobs/<job_id>/details` | Get detailed job info |

## Search Algorithms

- `text_search` - Keyword-based text matching (default)
- `fuzzy_search` - Fuzzy matching with typo tolerance

## Adding New Algorithms

Extend `SearchAlgorithm` base class in `search_algorithms.py`:

```python
class MyAlgorithm(SearchAlgorithm):
    @property
    def name(self) -> str:
        return "my_algorithm"
    
    def search(self, query: str, videos: List[Dict]) -> List[Dict]:
        # Your implementation
        pass

# Register it
SearchAlgorithmFactory.register_algorithm('my_algorithm', MyAlgorithm)
```
