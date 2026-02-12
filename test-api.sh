#!/bin/bash

# CloudNest API Testing Script
# This script provides example API calls for testing

API_URL="http://localhost:8000"

echo "========================================="
echo "   CloudNest API Test Script 🧪"
echo "========================================="
echo ""

# Function to print section headers
section() {
    echo ""
    echo "========================================="
    echo "   $1"
    echo "========================================="
}

# Function to print test descriptions
test() {
    echo ""
    echo "→ $1"
    echo ""
}

section "1. Health Check"
test "Check if API is running"
curl -X GET $API_URL/health | jq .
sleep 1

section "2. User Registration"
test "Register a new user"
curl -X POST $API_URL/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123",
    "username": "testuser"
  }' | jq .

echo ""
echo "⚠ Check your email for verification link!"
echo "Press Enter when you have verified your email..."
read

section "3. User Login"
test "Login with credentials"
LOGIN_RESPONSE=$(curl -s -X POST $API_URL/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123"
  }')

echo $LOGIN_RESPONSE | jq .

# Extract token
TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.token')

if [ "$TOKEN" != "null" ]; then
    echo ""
    echo "✓ Login successful! Token obtained."
else
    echo ""
    echo "✗ Login failed. Make sure email is verified."
    exit 1
fi

section "4. Get Current User Info"
test "Get authenticated user information"
curl -X GET $API_URL/auth/me \
  -H "Authorization: Bearer $TOKEN" | jq .

section "5. Create Application"
test "Create a new application"
curl -X POST $API_URL/apps/create \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "test-app",
    "git_url": "https://github.com/example/repo.git",
    "branch": "main",
    "env_vars": {
      "NODE_ENV": "production"
    }
  }' | jq .

section "6. List Applications"
test "List all applications"
curl -X GET $API_URL/apps/list \
  -H "Authorization: Bearer $TOKEN" | jq .

section "7. Forgot Password"
test "Request password reset"
curl -X POST $API_URL/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com"
  }' | jq .

echo ""
echo "========================================="
echo "   Testing Complete! ✓"
echo "========================================="
echo ""
echo "Your JWT Token (save this for further testing):"
echo $TOKEN
echo ""
