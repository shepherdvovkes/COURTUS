# CourtListener API Performance Testing

This script tests the CourtListener API with different concurrency levels and requests per second (RPS) rates to measure performance and identify optimal parameters.

## Setup

1. Create a virtual environment (recommended):
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your API key:
```bash
# Create .env file and add:
COURTLISTENER_API_KEY=your_api_key_here
```

## Usage

### Basic Usage

Run with default parameters (tests concurrency levels: 1, 5, 10, 20):
```bash
# Make sure virtual environment is activated
source venv/bin/activate  # On Windows: venv\Scripts\activate
python test_courtlistener_api.py
```

### Custom Concurrency Levels

Test specific concurrency levels:
```bash
python test_courtlistener_api.py --concurrency 5 10 20 50
```

### Test with Rate Limiting (RPS)

Test with specific requests per second limits:
```bash
python test_courtlistener_api.py --rps 10 20 50
```

### Single Test

Run a single test with specific parameters:
```bash
python test_courtlistener_api.py --single-test --concurrency 10 --rps 20 --requests 50
```

### Custom Endpoint

Test a different API endpoint:
```bash
python test_courtlistener_api.py --endpoint "dockets/" --requests 100
```

### All Options

```bash
python test_courtlistener_api.py \
  --endpoint "search/" \
  --requests 200 \
  --concurrency 5 10 20 \
  --rps 0 10 20 \
  --timeout 30
```

## Parameters

- `--endpoint`: API endpoint to test (default: `search/`)
- `--requests`: Total number of requests to make (default: 100)
- `--concurrency`: Concurrency levels to test, space-separated (default: 1 5 10 20)
- `--rps`: Requests per second to test, space-separated. Use 0 for unlimited (default: 0)
- `--timeout`: Request timeout in seconds (default: 30)
- `--single-test`: Run a single test instead of multiple combinations

## Output

The script provides detailed statistics for each test:
- Total requests and success/failure counts
- Response time statistics (average, median, min, max, P95, P99)
- Throughput (requests per second)
- Status code distribution

At the end, a comparison table shows all test results side-by-side.
