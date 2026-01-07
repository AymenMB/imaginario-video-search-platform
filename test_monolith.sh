#!/bin/bash

# Test script for the monolith application
# This verifies that the backend is working correctly

echo "Testing Monolith Backend..."
echo "============================"

BASE_URL="http://localhost:5000"

# Test 1: Health check
echo -e "\n1. Testing health endpoint..."
curl -s "$BASE_URL/health" | jq '.' || echo "Health check failed"

# Test 2: Register user
echo -e "\n2. Registering test user..."
REGISTER_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123","name":"Test User"}')
echo "$REGISTER_RESPONSE" | jq '.'

TOKEN=$(echo "$REGISTER_RESPONSE" | jq -r '.token')
USER_ID=$(echo "$REGISTER_RESPONSE" | jq -r '.user.id')

if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
  echo "Registration failed or user already exists. Trying login..."
  LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"test123"}')
  TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.token')
  USER_ID=$(echo "$LOGIN_RESPONSE" | jq -r '.user.id')
fi

echo "Token: ${TOKEN:0:20}..."
echo "User ID: $USER_ID"

# Test 3: Create video
echo -e "\n3. Creating a video..."
CREATE_VIDEO=$(curl -s -X POST "$BASE_URL/api/v1/users/$USER_ID/videos" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"title":"Test Video","description":"This is a test video for search","duration":120}')
echo "$CREATE_VIDEO" | jq '.'
VIDEO_ID=$(echo "$CREATE_VIDEO" | jq -r '.id')

# Test 4: List videos
echo -e "\n4. Listing videos..."
curl -s -X GET "$BASE_URL/api/v1/users/$USER_ID/videos" \
  -H "Authorization: Bearer $TOKEN" | jq '.'

# Test 5: Create API key
echo -e "\n5. Creating API key..."
API_KEY_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/api-keys" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"Test API Key"}')
echo "$API_KEY_RESPONSE" | jq '.'
API_KEY=$(echo "$API_KEY_RESPONSE" | jq -r '.api_key')

# Test 6: List API keys
echo -e "\n6. Listing API keys..."
curl -s -X GET "$BASE_URL/api/v1/auth/api-keys" \
  -H "Authorization: Bearer $TOKEN" | jq '.'

# Test 7: Search (using API key)
echo -e "\n7. Testing search with API key..."
SEARCH_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/users/$USER_ID/search" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{"query":"test"}')
echo "$SEARCH_RESPONSE" | jq '.'
JOB_ID=$(echo "$SEARCH_RESPONSE" | jq -r '.job_id')

# Test 8: Get search results
if [ "$JOB_ID" != "null" ] && [ -n "$JOB_ID" ]; then
  echo -e "\n8. Getting search results..."
  sleep 1
  curl -s -X GET "$BASE_URL/api/v1/users/$USER_ID/search/$JOB_ID" \
    -H "Authorization: Bearer $API_KEY" | jq '.'
fi

echo -e "\n============================"
echo "Tests completed!"

