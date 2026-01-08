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

## Maximum Concurrency Testing

Use `measure_max_concurrency.py` to find the maximum concurrency limit that the API can handle.

### Binary Search Method (Fast)

Uses binary search to quickly find the maximum concurrency:
```bash
python measure_max_concurrency.py --method binary --requests 100 --max 10000
```

### Linear Search Method (Detailed)

Tests each concurrency level sequentially for detailed analysis:
```bash
python measure_max_concurrency.py --method linear --requests 50 --start 1 --max 1000 --step 10
```

### Options

- `--endpoint`: API endpoint to test (default: `search/`)
- `--requests`: Number of requests per test (default: 100)
- `--start`: Starting concurrency level (default: 1)
- `--max`: Maximum concurrency to test (default: 10000)
- `--step`: Step size for linear search (default: 10)
- `--threshold`: Success rate threshold percentage (default: 95.0)
- `--timeout`: Request timeout in seconds (default: 30)
- `--method`: Search method - `binary` (fast) or `linear` (detailed) (default: binary)
- `--stop-on-failure`: Stop linear search on first failure
- `--verbose`: Show detailed results for each test

### Example: Find Maximum Concurrency

```bash
# Quick binary search
python measure_max_concurrency.py --method binary --requests 200 --max 5000

# Detailed linear search with stopping on failure
python measure_max_concurrency.py --method linear --requests 100 --start 1 --max 2000 --step 50 --stop-on-failure
```
