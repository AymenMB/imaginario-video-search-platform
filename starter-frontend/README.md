# Video Search Platform - Frontend Starter

This is a starter Next.js frontend application. Candidates need to complete the TODO items marked in the code.

## Setup

1. Install dependencies:
```bash
npm install
# or
yarn install
```

2. Set environment variables:
Create a `.env.local` file:
```
NEXT_PUBLIC_API_URL=http://localhost:5000
```

3. Run development server:
```bash
npm run dev
# or
yarn dev
```

The app will be available at `http://localhost:3000`

## Pages Structure

### Implemented (Basic Structure)
- `/` - Dashboard/Home page (structure only)
- `/login` - Login page (needs completion)
- `/register` - Registration page (needs completion)
- `/api-keys` - API Keys management page (structure only)

### TODO - Candidates Need to Implement

1. **Dashboard (`/`)**:
   - Video library display (grid or list)
   - Search bar and search functionality
   - Create video button and form
   - Video cards with details
   - Loading and error states

2. **Search Functionality**:
   - Search input and submit
   - Poll search job status
   - Display search results
   - Handle search errors

3. **API Keys Page (`/api-keys`)**:
   - List API keys
   - Create new API key
   - Display API key (once after creation)
   - Delete API key
   - Copy to clipboard

4. **Video Management**:
   - Create video form/modal
   - Edit video form/modal
   - Delete video with confirmation
   - Video detail view (optional)

## Components to Create

Candidates should create reusable components:
- `VideoCard` - Display video information
- `SearchBar` - Search input and submit
- `SearchResults` - Display search results
- `VideoForm` - Create/edit video form
- `ApiKeyCard` - Display API key information
- `LoadingSpinner` - Loading indicator
- `ErrorMessage` - Error display component

## State Management

The Redux store is set up but empty. Candidates should:
1. Create slices for:
   - `authSlice` - User authentication state
   - `videoSlice` - Video list and operations
   - `searchSlice` - Search state and results
   - `apiKeySlice` - API keys state

2. Implement actions and reducers for each slice

## API Client

The API client (`lib/api.ts`) has basic structure but needs:
1. Complete all API methods
2. Proper error handling
3. Token management
4. Request/response interceptors

## Styling

The project uses Tailwind CSS. Candidates can:
- Use Tailwind utility classes
- Create custom components
- Add animations/transitions (bonus)

## Key Features to Implement

1. **Authentication Flow**:
   - Login/register
   - Token storage
   - Protected routes
   - Auto-logout on 401

2. **Video Library**:
   - List videos
   - Create video
   - Edit video
   - Delete video
   - Pagination (bonus)

3. **Search**:
   - Submit search query
   - Poll job status
   - Display results
   - Handle errors

4. **API Keys**:
   - Create API key
   - List API keys
   - Delete API key
   - Copy to clipboard

