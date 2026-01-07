# Fullstack Developer Technical Assignment
## Imaginario - Final Year Intern Position

### Overview

This assignment is designed to assess both your backend and frontend skills while working on a project that mirrors the real-world challenges we face at Imaginario. You'll be working with a **working monolith application** and your task is to **break it down into microservices** and **create a developer dashboard**.

**Time Estimate:** 8-10 hours  
**Submission:** GitHub repository with README and setup instructions

---

## The Challenge

You'll receive a **fully functional monolith application** (backend + frontend) that implements a video search platform. Your task is to:

1. **Break down the monolith into microservices**:
   - Extract search functionality into a separate Search Microservice
   - Create an API Gateway that routes requests and listens to the microservices
   - Maintain the same API interface

2. **Refactor for production quality**:
   - Apply software engineering best practices
   - Structure the codebase for maintainability and extensibility
   - Make the search functionality extensible for future algorithms

3. **Create a Developer Dashboard**:
   - Build a new **Developer Dashboard** for API users
   - Track API usage statistics and analytics
   - Monitor search jobs in real-time
   - View usage per API key
   - Professional UI for developers using the API

---

## What You'll Receive

### Working Monolith Application

**Backend (`starter-backend/`):**
- ✅ Fully functional Flask application
- ✅ User authentication (JWT + API keys)
- ✅ Video CRUD operations
- ✅ Search functionality (text-based)
- ✅ API key management
- ✅ All endpoints working

**Frontend (`starter-frontend/`):**
- ✅ Next.js application with TypeScript
- ✅ Login/Register pages
- ✅ Video library dashboard
- ✅ Search functionality
- ✅ API key management page
- ✅ Redux state management
- ✅ All features working

---

## Your Tasks

### Part 1: Microservices Architecture (40%)

#### 1.1 Create Search Microservice

Extract the search functionality into a separate Flask microservice:

**New Service: `search-microservice/`**
- Create a new Flask application
- Move search logic to this service
- Implement endpoints:
  - `POST /api/v1/search/jobs` - Submit search job
  - `GET /api/v1/search/jobs/<job_id>` - Get search results
- Store search jobs in database (SQLite is fine)
- Process searches asynchronously
- Design the search capability to support multiple search algorithms in the future

**Requirements:**
- Separate Flask application
- Own database for search jobs
- Service-to-service authentication (simple token or API key)
- Health check endpoint

#### 1.2 Create API Gateway

Modify the existing backend to become an API Gateway:

**Modify: `starter-backend/` → `api-gateway/`**
- Keep all existing endpoints working
- Remove search logic from API Gateway
- Add Search Microservice client
- Route search requests to Search Microservice:
  - `POST /api/v1/users/<user_id>/search` → calls Search Microservice
  - `GET /api/v1/users/<user_id>/search/<job_id>` → calls Search Microservice
- Handle service-to-service communication
- Maintain backward compatibility (same API interface)

**Requirements:**
- All existing endpoints still work
- Search requests routed to microservice
- Proper error handling for microservice failures
- Service discovery/configuration

#### 1.3 Communication Pattern

**API Gateway → Search Microservice:**
- Use HTTP REST calls
- Service-to-service authentication
- Handle timeouts and errors
- Return appropriate error messages to clients

**Example Flow:**
```
1. Client → API Gateway: POST /api/v1/users/1/search
2. API Gateway → Search Microservice: POST /api/v1/search/jobs
3. Search Microservice: Process search, return job_id
4. API Gateway → Client: Return job_id
5. Client → API Gateway: GET /api/v1/users/1/search/<job_id>
6. API Gateway → Search Microservice: GET /api/v1/search/jobs/<job_id>
7. Search Microservice: Return results
8. API Gateway → Client: Return results
```

---

### Part 2: Create Developer Dashboard (Frontend - 40%)

#### 2.1 Developer Dashboard for API Users

Create a new **Developer Dashboard** page: `/developer-dashboard` 

This dashboard is specifically for **API users** (developers using API keys) to monitor their usage and track their jobs.

**Features to Implement:**

1. **API Usage Analytics**:
   - Total API requests (today, this week, this month)
   - Requests per endpoint (videos, search, etc.)
   - Success vs error rate
   - Response time metrics (average, p95, p99)
   - Charts/graphs showing usage trends over time
   - Usage by API key (if user has multiple keys)

2. **Search Job Tracking**:
   - List of all search jobs submitted via API
   - Real-time job status (queued, processing, completed, failed)
   - Search query for each job
   - Job execution time
   - Results preview (number of results, top results)
   - Ability to view full search results
   - Filter/search jobs by status, date, query

3. **API Key Management** (enhance existing):
   - Usage statistics per API key
   - Requests count per key
   - Last used timestamp
   - Active/inactive status
   - Revoke/delete keys
   - Create new API keys

4. **Usage Quotas & Limits** (if implemented):
   - Current quota usage (daily/monthly)
   - Remaining requests
   - Quota reset times
   - Visual indicators for quota consumption

#### 2.2 Backend Endpoints (You Need to Add)

Add new endpoints to support the developer dashboard:

**Usage Analytics:**
- `GET /api/v1/analytics/usage` - Get API usage statistics
  - Query params: `start_date`, `end_date`, `api_key_id` (optional)
  - Returns: total requests, requests per endpoint, error rate, response times

- `GET /api/v1/analytics/usage/daily` - Daily usage breakdown
- `GET /api/v1/analytics/usage/endpoints` - Usage per endpoint

**Search Jobs:**
- `GET /api/v1/search/jobs` - List all search jobs for user
  - Query params: `status`, `start_date`, `end_date`, `page`, `per_page`
  - Returns: paginated list of search jobs with metadata

- `GET /api/v1/search/jobs/<job_id>/details` - Get detailed job information

**API Key Usage:**
- `GET /api/v1/auth/api-keys/<key_id>/usage` - Get usage stats for specific API key
- `GET /api/v1/auth/api-keys/<key_id>/usage/daily` - Daily usage for API key

---

### Part 3: Code Quality & Testing (20%)

#### 3.1 Code Quality

- Structure your code for maintainability
- Write clean, readable, well-organized code
- Ensure your code is testable
- Apply appropriate software design principles

#### 3.2 Testing

- Write unit tests for your business logic
- Tests should be isolated and not depend on external services
- Demonstrate that components can be tested independently

#### 3.3 Documentation

In your `README.md`, include a **"Design Decisions"** section that covers:

1. **Architecture Overview**: How your services are structured and why
2. **Key Design Decisions**: Explain the patterns or approaches you chose
3. **Trade-offs**: Document any trade-offs you made and justify your decisions
4. **Improvements**: What would you improve if you had more time?

---

## Technical Requirements

### Microservices Architecture

1. **Service Independence**:
   - Each service has its own database
   - Services communicate via HTTP REST
   - No shared database connections

2. **Service Discovery**:
   - Use environment variables for service URLs
   - Example: `SEARCH_MICROSERVICE_URL=http://localhost:5001`

3. **Error Handling**:
   - Handle microservice unavailability
   - Return appropriate HTTP status codes
   - Log errors for debugging

4. **Authentication**:
   - Service-to-service authentication
   - Simple token or API key approach

### Developer Dashboard Requirements

1. **Real-time Job Tracking**:
   - Auto-refresh search job status
   - Poll for job updates
   - Show live job progress
   - Notifications for completed/failed jobs

2. **Data Visualization**:
   - Use charts (Chart.js, Recharts, or similar)
   - Show usage trends over time (line charts)
   - Requests per endpoint (bar charts)
   - Error rate visualization
   - Response time distribution
   - Make it visually appealing and professional

3. **User Experience**:
   - Clean, developer-focused UI
   - Responsive design (works on desktop and tablet)
   - Loading states for all async operations
   - Error handling with user-friendly messages
   - Export functionality (CSV/JSON) for usage data (bonus)

4. **Job Management**:
   - View job details (query, status, results count)
   - Retry failed jobs (if applicable)
   - Cancel running jobs (if applicable)
   - Filter and search jobs

5. **API Key Insights**:
   - Usage comparison across multiple API keys
   - Identify which keys are most/least used
   - Track key performance

---

## Deliverables

1. **GitHub Repository** with:
   - `api-gateway/` - Modified backend (API Gateway)
   - `search-microservice/` - New search microservice
   - `starter-frontend/` - Enhanced frontend with dashboard
   - `tests/` - Unit tests
   - `README.md` with:
     - Architecture overview
     - Setup instructions for all services
     - How to run the microservices
     - API documentation
     - **Design Decisions section**

2. **Documentation:**
   - Architecture diagram (text or image)
   - Service communication flow
   - Design decisions and trade-offs
   - How to test the system

---

## Evaluation Criteria

### Microservices Implementation (40%)
| Criteria | Description |
|----------|-------------|
| **Service Extraction** | Search functionality correctly extracted into separate microservice |
| **API Gateway** | Properly routes requests, handles errors, maintains backward compatibility |
| **Communication** | Service-to-service communication works reliably with proper auth |
| **Resilience** | Graceful handling of microservice failures |

### Developer Dashboard (40%)
| Criteria | Description |
|----------|-------------|
| **Functionality** | All required features implemented (analytics, job tracking, API keys) |
| **Data Visualization** | Charts/graphs effectively display usage trends |
| **Real-time Updates** | Job status updates work correctly |
| **Backend Endpoints** | Analytics endpoints properly implemented |
| **UI/UX Quality** | Professional, developer-focused, responsive design |

### Code Quality & Design (20%)
| Criteria | Description |
|----------|-------------|
| **Code Organization** | Clean, maintainable, well-structured codebase |
| **Design Decisions** | Thoughtful architecture and pattern choices |
| **Testability** | Code is structured for easy testing |
| **Documentation** | Clear explanation of design decisions and trade-offs |

---

## Bonus Points

- ✅ Docker Compose setup for all services
- ✅ Comprehensive test coverage
- ✅ API documentation (Swagger/OpenAPI)
- ✅ Circuit breaker pattern implementation
- ✅ Advanced analytics (trends, predictions)
- ✅ Export functionality (CSV/JSON) for usage data
- ✅ Job retry/cancel functionality
- ✅ Request/response logging and debugging tools
- ✅ Real-time notifications (WebSockets)

---

## Setup Instructions

### Running the Monolith (Starting Point)

**Backend:**
```bash
cd starter-backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

**Frontend:**
```bash
cd starter-frontend
npm install
# Create .env.local: NEXT_PUBLIC_API_URL=http://localhost:5000
npm run dev
```

### Your Implementation

You should provide setup instructions for:
- API Gateway
- Search Microservice
- Frontend (with dashboard)
- How to run all services together
- How to run tests

---

## Tips

1. **Start with Architecture**: Plan your approach before coding
2. **Incremental Approach**: Extract search service first, then enhance
3. **Test Each Service**: Make sure each service works independently
4. **Maintain Compatibility**: Keep the same API interface
5. **Documentation**: Good documentation shows communication skills

---

## Questions?

If you have any questions about the requirements, feel free to reach out. We're looking for:
- Problem-solving ability
- Understanding of microservices architecture
- Code quality and organization
- Fullstack development skills
- Ability to work with existing codebase
- Clear communication through documentation

Good luck! 🚀
