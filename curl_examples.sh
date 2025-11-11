#!/bin/bash
# FastAPI Authentication Test Commands
#
# Usage: Make sure your .env file has TELEGRAM_AUTH_TOKEN set, then run:
# source .env && bash curl_examples.sh

echo "🚀 Testing FastAPI Authentication"
echo "================================="

if [ -z "$TELEGRAM_AUTH_TOKEN" ]; then
    echo "❌ Error: TELEGRAM_AUTH_TOKEN environment variable not set"
    echo "Please add TELEGRAM_AUTH_TOKEN=your_token_here to your .env file"
    exit 1
fi

echo "📍 Using token: ${TELEGRAM_AUTH_TOKEN:0:8}..."
echo ""

# Test public endpoints (no auth required)
echo "📖 Testing public endpoints:"
echo "GET / (root)"
curl -s http://localhost:8000/ | jq -r '.message' 2>/dev/null || curl -s http://localhost:8000/
echo ""

echo "GET /health"
curl -s http://localhost:8000/health | jq -r '.status' 2>/dev/null || curl -s http://localhost:8000/health
echo ""
echo ""

# Test protected endpoint without auth (should fail)
echo "🚫 Testing protected endpoint WITHOUT authentication (should fail):"
echo "GET /webhook/info"
curl -s -w "HTTP Status: %{http_code}\n" http://localhost:8000/webhook/info
echo ""

# Test protected endpoints with auth (should succeed)
echo "🔐 Testing protected endpoints WITH authentication:"
echo "GET /webhook/info"
curl -s -H "Authorization: Bearer $TELEGRAM_AUTH_TOKEN" http://localhost:8000/webhook/info | jq '.' 2>/dev/null || curl -s -H "Authorization: Bearer $TELEGRAM_AUTH_TOKEN" http://localhost:8000/webhook/info
echo ""

echo "POST /webhook/set (example with test URL)"
curl -s -X POST \
  -H "Authorization: Bearer $TELEGRAM_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  "http://localhost:8000/webhook/set?webhook_url=https://example.com/test" | jq '.' 2>/dev/null || curl -s -X POST -H "Authorization: Bearer $TELEGRAM_AUTH_TOKEN" "http://localhost:8000/webhook/set?webhook_url=https://example.com/test"
echo ""

echo "✅ Authentication tests completed!"
echo ""
echo "💡 Manual curl examples:"
echo "   # Get webhook info:"
echo "   curl -H 'Authorization: Bearer $TELEGRAM_AUTH_TOKEN' http://localhost:8000/webhook/info"
echo ""
echo "   # Set webhook:"
echo "   curl -X POST -H 'Authorization: Bearer $TELEGRAM_AUTH_TOKEN' \\"
echo "        'http://localhost:8000/webhook/set?webhook_url=https://yourdomain.com/webhook/tg-nqlftdvdqi'"
echo ""
echo "   # Delete webhook:"
echo "   curl -X DELETE -H 'Authorization: Bearer $TELEGRAM_AUTH_TOKEN' http://localhost:8000/webhook"
