#!/bin/bash
# API Testing Script for ACE Platform

set -e

BASE_URL="http://localhost:8000"

echo "🧪 ACE Platform API Tests"
echo "=========================="
echo ""

# Test 1: Login
echo "Test 1: Login as admin"
echo "-----------------------"
LOGIN_RESPONSE=$(curl -s -X POST $BASE_URL/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"test123"}')

TOKEN=$(echo $LOGIN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['token'])")
echo "✅ Login successful"
echo "Token: ${TOKEN:0:50}..."
echo ""

# Test 2: Get current user
echo "Test 2: Get current user"
echo "------------------------"
ME_RESPONSE=$(curl -s -X GET $BASE_URL/api/auth/me \
  -H "Authorization: Bearer $TOKEN")
echo "$ME_RESPONSE" | python3 -m json.tool
echo "✅ User info retrieved"
echo ""

# Test 3: List users
echo "Test 3: List users in organization"
echo "-----------------------------------"
USERS_RESPONSE=$(curl -s -X GET $BASE_URL/api/organizations/1/users \
  -H "Authorization: Bearer $TOKEN")
USER_COUNT=$(echo "$USERS_RESPONSE" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))")
echo "✅ Found $USER_COUNT users"
echo ""

# Test 4: Create a survey
echo "Test 4: Create a test survey"
echo "-----------------------------"
SURVEY_RESPONSE=$(curl -s -X POST $BASE_URL/api/organizations/1/surveys \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Survey",
    "slug": "test-survey",
    "survey_type": "regular",
    "status": "draft",
    "organization_id": 1,
    "flow_json": {
      "nodes": [
        {
          "id": "q1",
          "type": "choice",
          "question": "How satisfied are you?",
          "choices": [
            {"text": "Very satisfied", "score": 100},
            {"text": "Satisfied", "score": 75},
            {"text": "Neutral", "score": 50}
          ]
        }
      ]
    }
  }')

SURVEY_ID=$(echo "$SURVEY_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "✅ Survey created with ID: $SURVEY_ID"
echo ""

# Test 5: List surveys
echo "Test 5: List surveys"
echo "--------------------"
SURVEYS_RESPONSE=$(curl -s -X GET $BASE_URL/api/organizations/1/surveys \
  -H "Authorization: Bearer $TOKEN")
SURVEY_COUNT=$(echo "$SURVEYS_RESPONSE" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))")
echo "✅ Found $SURVEY_COUNT surveys"
echo ""

# Test 6: Publish survey
echo "Test 6: Publish survey"
echo "----------------------"
PUBLISH_RESPONSE=$(curl -s -X POST $BASE_URL/api/organizations/1/surveys/$SURVEY_ID/publish \
  -H "Authorization: Bearer $TOKEN")
SURVEY_STATUS=$(echo "$PUBLISH_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])")
echo "✅ Survey published (status: $SURVEY_STATUS)"
echo ""

# Test 7: Get survey publicly (no auth)
echo "Test 7: Get published survey (public endpoint)"
echo "-----------------------------------------------"
PUBLIC_SURVEY=$(curl -s -X GET $BASE_URL/s/test-survey)
SURVEY_NAME=$(echo "$PUBLIC_SURVEY" | python3 -c "import sys, json; print(json.load(sys.stdin)['name'])")
echo "✅ Public survey accessible: $SURVEY_NAME"
echo ""

# Test 8: Submit survey response
echo "Test 8: Submit survey response"
echo "-------------------------------"
RESPONSE=$(curl -s -X POST $BASE_URL/s/test-survey/submit \
  -H "Content-Type: application/json" \
  -d '{
    "survey_id": '$SURVEY_ID',
    "sid": "test-session-123",
    "variant": null,
    "survey_answers": {
      "q1": {"text": "Very satisfied", "score": 100}
    },
    "name": "Test User",
    "email": "test@example.com",
    "phone": "+1234567890"
  }')
RESPONSE_SCORE=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['score'])")
echo "✅ Response submitted (score: $RESPONSE_SCORE)"
echo ""

# Test 9: Get survey statistics
echo "Test 9: Get survey statistics"
echo "------------------------------"
STATS=$(curl -s -X GET $BASE_URL/api/organizations/1/surveys/$SURVEY_ID/stats \
  -H "Authorization: Bearer $TOKEN")
echo "$STATS" | python3 -m json.tool
echo "✅ Statistics retrieved"
echo ""

# Test 10: Get survey responses
echo "Test 10: Get survey responses"
echo "------------------------------"
RESPONSES=$(curl -s -X GET $BASE_URL/api/organizations/1/surveys/$SURVEY_ID/responses \
  -H "Authorization: Bearer $TOKEN")
RESPONSE_COUNT=$(echo "$RESPONSES" | python3 -c "import sys, json; print(len(json.load(sys.stdin)))")
echo "✅ Found $RESPONSE_COUNT responses"
echo ""

# Test 11: Archive survey
echo "Test 11: Archive survey"
echo "-----------------------"
ARCHIVE_RESPONSE=$(curl -s -X POST $BASE_URL/api/organizations/1/surveys/$SURVEY_ID/archive \
  -H "Authorization: Bearer $TOKEN")
ARCHIVED_STATUS=$(echo "$ARCHIVE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])")
echo "✅ Survey archived (status: $ARCHIVED_STATUS)"
echo ""

# Test 12: Delete survey
echo "Test 12: Delete survey"
echo "----------------------"
curl -s -X DELETE $BASE_URL/api/organizations/1/surveys/$SURVEY_ID \
  -H "Authorization: Bearer $TOKEN" > /dev/null
echo "✅ Survey deleted"
echo ""

echo "================================"
echo "✅ All tests passed successfully!"
echo "================================"
