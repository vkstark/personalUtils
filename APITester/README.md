# APITester - HTTP API Testing Tool

Quick and friendly HTTP API testing tool - simpler than curl, with automatic JSON formatting and request history.

## Features

- **Simple Interface**
  - Easy command-line syntax
  - Automatic JSON handling
  - Color-coded status codes

- **Request Support**
  - All HTTP methods (GET, POST, PUT, DELETE, etc.)
  - Custom headers
  - JSON request bodies
  - Timeout configuration

- **Response Handling**
  - Automatic JSON parsing and formatting
  - Response time tracking
  - Header display option
  - Status code highlighting

- **History Tracking**
  - Automatic request history
  - Last 100 requests saved
  - View recent requests

## Installation

```bash
chmod +x api_tester.py
# Optional: Create symlink
ln -s $(pwd)/api_tester.py ~/bin/api
```

## Usage

### Basic Requests

**GET request:**
```bash
# Simple GET
./api_tester.py GET https://api.github.com

# With query parameters
./api_tester.py GET "https://api.example.com/search?q=test"
```

**POST request:**
```bash
# POST with JSON
./api_tester.py POST https://api.example.com/users -d '{"name":"John","email":"john@example.com"}'

# POST from variable
DATA='{"title":"Test","body":"Content"}'
./api_tester.py POST https://jsonplaceholder.typicode.com/posts -d "$DATA"
```

**Other methods:**
```bash
# PUT
./api_tester.py PUT https://api.example.com/users/1 -d '{"name":"Jane"}'

# DELETE
./api_tester.py DELETE https://api.example.com/users/1

# PATCH
./api_tester.py PATCH https://api.example.com/users/1 -d '{"active":true}'
```

### Custom Headers

**Single header:**
```bash
./api_tester.py GET https://api.example.com/protected \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Multiple headers:**
```bash
./api_tester.py POST https://api.example.com/data \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Custom-Header: value" \
  -d '{"key":"value"}'
```

### Response Options

**Show headers:**
```bash
./api_tester.py GET https://api.example.com --show-headers
```

**Disable colors:**
```bash
./api_tester.py GET https://api.example.com --no-color
```

**Set timeout:**
```bash
./api_tester.py GET https://slow-api.com -t 60  # 60 seconds
```

### History

**View recent requests:**
```bash
# Last 10 requests (default)
./api_tester.py --history

# Last 20 requests
./api_tester.py --history --limit 20
```

## Output Examples

### Successful Request
```
Requesting: GET https://api.github.com

Status: 200 | Time: 0.245s

Response (JSON):
{
  "current_user_url": "https://api.github.com/user",
  "authorizations_url": "https://api.github.com/authorizations",
  ...
}
```

### Failed Request
```
Requesting: GET https://api.example.com/notfound

Status: 404 | Time: 0.123s

Response (JSON):
{
  "error": "Not Found",
  "message": "The requested resource was not found"
}
```

### With Headers
```
Requesting: GET https://api.example.com

Status: 200 | Time: 0.156s

Headers:
  Content-Type: application/json
  X-RateLimit-Limit: 60
  X-RateLimit-Remaining: 59

Response (JSON):
{ ... }
```

### History View
```
Recent Requests:

1. [2024-11-08 16:30:25] GET https://api.github.com
   Status: 200 | Time: 0.245s

2. [2024-11-08 16:29:10] POST https://api.example.com/users
   Status: 201 | Time: 0.321s

3. [2024-11-08 16:28:45] DELETE https://api.example.com/users/1
   Status: 204 | Time: 0.198s
```

## Common Use Cases

### API Development
```bash
# Test your API endpoints
./api_tester.py GET http://localhost:8000/api/users
./api_tester.py POST http://localhost:8000/api/users -d '{"name":"Test"}'
```

### Third-Party APIs
```bash
# GitHub API
./api_tester.py GET https://api.github.com/users/octocat

# JSONPlaceholder (testing API)
./api_tester.py GET https://jsonplaceholder.typicode.com/posts/1
./api_tester.py POST https://jsonplaceholder.typicode.com/posts \
  -d '{"title":"Test","body":"Content","userId":1}'
```

### Authenticated Requests
```bash
# Bearer token
./api_tester.py GET https://api.example.com/protected \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# API key
./api_tester.py GET https://api.example.com/data \
  -H "X-API-Key: YOUR_API_KEY"

# Basic auth (base64 encoded)
./api_tester.py GET https://api.example.com/secure \
  -H "Authorization: Basic BASE64_CREDENTIALS"
```

### Testing Webhooks
```bash
# Send webhook payload
./api_tester.py POST https://your-app.com/webhook \
  -d '{"event":"user.created","data":{"id":123,"name":"John"}}'
```

## Command Line Options

```
positional arguments:
  method                HTTP method (GET, POST, PUT, DELETE, etc.)
  url                   URL to request

request options:
  -d, --data           Request body (JSON string)
  -H, --header         Custom header (repeatable)
  -t, --timeout        Timeout in seconds (default: 30)

display options:
  --show-headers       Show response headers
  --no-color           Disable colored output
  -v, --verbose        Verbose output

history:
  --history            Show request history
  --limit N            History limit (default: 10)

other:
  --version            Show version
  -h, --help           Show help message
```

## Status Code Colors

- **Green (2xx)**: Success
- **Yellow (3xx)**: Redirection
- **Red (4xx, 5xx)**: Client/Server Error

## Tips

1. **Use quotes** for URLs with query parameters
2. **Single quotes** for JSON data to avoid shell interpretation
3. **Check history** to repeat previous requests
4. **Set longer timeouts** for slow APIs
5. **Use --show-headers** to debug issues

## Comparison with curl

**curl:**
```bash
curl -X POST https://api.example.com/users \
  -H "Content-Type: application/json" \
  -d '{"name":"John"}' | jq
```

**APITester (simpler):**
```bash
./api_tester.py POST https://api.example.com/users -d '{"name":"John"}'
```

## Exit Codes

- `0` - Success (2xx status)
- `1` - Error (4xx, 5xx, or network error)
- `130` - Cancelled by user

## History Storage

History is stored in `~/.api_tester_history.json` (last 100 requests)

## Author

Vishal Kumar

## License

MIT
