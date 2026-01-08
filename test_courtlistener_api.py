#!/usr/bin/env python3
"""
CourtListener API Performance Testing Script

This script tests the CourtListener API with different concurrency levels
and requests per second (RPS) rates to measure performance and identify
optimal parameters.
"""

import os
import time
import asyncio
import aiohttp
import argparse
from datetime import datetime
from typing import List, Dict, Tuple
from dataclasses import dataclass
from dotenv import load_dotenv
import statistics

# Load environment variables
load_dotenv()

@dataclass
class TestResult:
    """Stores results from a single API request"""
    status_code: int
    response_time: float
    success: bool
    error: str = ""

@dataclass
class TestSummary:
    """Summary of test run"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    median_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    duration: float
    status_codes: Dict[int, int]

class CourtListenerAPITester:
    """Tests CourtListener API with various concurrency and RPS parameters"""
    
    BASE_URL = "https://www.courtlistener.com/api/rest/v4"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Token {api_key}",
            "Content-Type": "application/json"
        }
        self.results: List[TestResult] = []
    
    async def make_request(self, session: aiohttp.ClientSession, endpoint: str) -> TestResult:
        """Make a single API request and measure response time"""
        start_time = time.time()
        try:
            url = f"{self.BASE_URL}/{endpoint}"
            async with session.get(url, headers=self.headers) as response:
                status_code = response.status
                response_time = time.time() - start_time
                success = 200 <= status_code < 300
                
                # Read response to get error details
                response_text = await response.text()
                
                error_msg = ""
                if not success:
                    # Try to extract error message from response
                    try:
                        import json
                        error_data = json.loads(response_text)
                        if 'detail' in error_data:
                            error_msg = f"HTTP {status_code}: {error_data['detail']}"
                        elif 'message' in error_data:
                            error_msg = f"HTTP {status_code}: {error_data['message']}"
                        else:
                            error_msg = f"HTTP {status_code}: {response_text[:200]}"
                    except:
                        error_msg = f"HTTP {status_code}: {response_text[:200] if response_text else 'No response body'}"
                
                return TestResult(
                    status_code=status_code,
                    response_time=response_time,
                    success=success,
                    error=error_msg if error_msg else ""
                )
        except asyncio.TimeoutError:
            return TestResult(
                status_code=0,
                response_time=time.time() - start_time,
                success=False,
                error="Timeout"
            )
        except aiohttp.ClientError as e:
            return TestResult(
                status_code=0,
                response_time=time.time() - start_time,
                success=False,
                error=f"ClientError: {str(e)}"
            )
        except Exception as e:
            return TestResult(
                status_code=0,
                response_time=time.time() - start_time,
                success=False,
                error=f"Exception: {type(e).__name__}: {str(e)}"
            )
    
    async def run_test(
        self,
        endpoint: str,
        num_requests: int,
        concurrency: int,
        rps: float = 0,
        timeout: int = 30
    ) -> TestSummary:
        """Run a test with specified parameters"""
        self.results = []
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(concurrency)
        
        # Rate limiting setup using token bucket approach
        if rps > 0:
            min_interval = 1.0 / rps
            last_request_time = [time.time()]
            rate_lock = asyncio.Lock()
            
            async def wait_for_rate_limit():
                async with rate_lock:
                    current_time = time.time()
                    elapsed = current_time - last_request_time[0]
                    if elapsed < min_interval:
                        sleep_time = min_interval - elapsed
                        last_request_time[0] = current_time + sleep_time
                        await asyncio.sleep(sleep_time)
                    else:
                        last_request_time[0] = current_time
        else:
            async def wait_for_rate_limit():
                pass  # No rate limiting
        
        timeout_config = aiohttp.ClientTimeout(total=timeout)
        
        start_time = time.time()
        
        async with aiohttp.ClientSession(timeout=timeout_config) as session:
            async def make_request_with_limiter():
                # Wait for rate limit
                await wait_for_rate_limit()
                
                # Concurrency limiting
                async with semaphore:
                    result = await self.make_request(session, endpoint)
                    self.results.append(result)
            
            tasks = [make_request_with_limiter() for _ in range(num_requests)]
            await asyncio.gather(*tasks)
        
        duration = time.time() - start_time
        
        return self._calculate_summary(duration)
    
    def _calculate_summary(self, duration: float) -> TestSummary:
        """Calculate summary statistics from results"""
        if not self.results:
            return TestSummary(
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                avg_response_time=0,
                min_response_time=0,
                max_response_time=0,
                median_response_time=0,
                p95_response_time=0,
                p99_response_time=0,
                requests_per_second=0,
                duration=duration,
                status_codes={}
            )
        
        successful = sum(1 for r in self.results if r.success)
        failed = len(self.results) - successful
        
        response_times = [r.response_time for r in self.results if r.success]
        
        if response_times:
            avg_rt = statistics.mean(response_times)
            min_rt = min(response_times)
            max_rt = max(response_times)
            median_rt = statistics.median(response_times)
            
            sorted_times = sorted(response_times)
            p95_idx = int(len(sorted_times) * 0.95)
            p99_idx = int(len(sorted_times) * 0.99)
            p95_rt = sorted_times[p95_idx] if p95_idx < len(sorted_times) else sorted_times[-1]
            p99_rt = sorted_times[p99_idx] if p99_idx < len(sorted_times) else sorted_times[-1]
        else:
            avg_rt = min_rt = max_rt = median_rt = p95_rt = p99_rt = 0
        
        status_codes = {}
        for result in self.results:
            status_codes[result.status_code] = status_codes.get(result.status_code, 0) + 1
        
        rps = len(self.results) / duration if duration > 0 else 0
        
        return TestSummary(
            total_requests=len(self.results),
            successful_requests=successful,
            failed_requests=failed,
            avg_response_time=avg_rt,
            min_response_time=min_rt,
            max_response_time=max_rt,
            median_response_time=median_rt,
            p95_response_time=p95_rt,
            p99_response_time=p99_rt,
            requests_per_second=rps,
            duration=duration,
            status_codes=status_codes
        )
    
    def print_summary(self, summary: TestSummary, test_name: str = ""):
        """Print formatted test summary"""
        print("\n" + "=" * 80)
        if test_name:
            print(f"Test: {test_name}")
        print("=" * 80)
        print(f"Total Requests:     {summary.total_requests}")
        print(f"Successful:         {summary.successful_requests} ({summary.successful_requests/summary.total_requests*100:.1f}%)")
        print(f"Failed:              {summary.failed_requests} ({summary.failed_requests/summary.total_requests*100:.1f}%)")
        print(f"\nResponse Times (seconds):")
        print(f"  Average:           {summary.avg_response_time:.3f}")
        print(f"  Median:            {summary.median_response_time:.3f}")
        print(f"  Min:               {summary.min_response_time:.3f}")
        print(f"  Max:               {summary.max_response_time:.3f}")
        print(f"  P95:               {summary.p95_response_time:.3f}")
        print(f"  P99:               {summary.p99_response_time:.3f}")
        print(f"\nThroughput:")
        print(f"  Requests/Second:   {summary.requests_per_second:.2f}")
        print(f"  Duration:          {summary.duration:.2f}s")
        print(f"\nStatus Codes:")
        for code, count in sorted(summary.status_codes.items()):
            print(f"  {code}: {count}")
        
        # Show error details if there are failures
        if summary.failed_requests > 0:
            errors = {}
            for result in self.results:
                if not result.success and result.error:
                    error_msg = result.error
                    errors[error_msg] = errors.get(error_msg, 0) + 1
            if errors:
                print(f"\nError Details:")
                for error, count in sorted(errors.items(), key=lambda x: x[1], reverse=True):
                    print(f"  {error}: {count}")
        
        print("=" * 80)


async def main():
    parser = argparse.ArgumentParser(
        description="Test CourtListener API with different concurrency and RPS parameters"
    )
    parser.add_argument(
        "--endpoint",
        type=str,
        default="search/",
        help="API endpoint to test (default: search/)"
    )
    parser.add_argument(
        "--requests",
        type=int,
        default=100,
        help="Total number of requests to make (default: 100)"
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        nargs="+",
        default=[1, 5, 10, 20],
        help="Concurrency levels to test (default: 1 5 10 20)"
    )
    parser.add_argument(
        "--rps",
        type=float,
        nargs="+",
        default=[0],
        help="Requests per second to test (0 = no limit, default: 0)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Request timeout in seconds (default: 30)"
    )
    parser.add_argument(
        "--single-test",
        action="store_true",
        help="Run a single test instead of multiple combinations"
    )
    
    args = parser.parse_args()
    
    # Get API key from environment
    api_key = os.getenv("COURTLISTENER_API_KEY")
    if not api_key:
        print("ERROR: COURTLISTENER_API_KEY not found in environment variables")
        print("Please create a .env file with COURTLISTENER_API_KEY=your_key")
        return
    
    tester = CourtListenerAPITester(api_key)
    
    print(f"CourtListener API Performance Test")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Endpoint: {args.endpoint}")
    print(f"Total Requests: {args.requests}")
    print(f"Timeout: {args.timeout}s")
    
    if args.single_test:
        # Run single test with first concurrency and RPS values
        concurrency = args.concurrency[0] if args.concurrency else 10
        rps = args.rps[0] if args.rps else 0
        
        test_name = f"Concurrency={concurrency}, RPS={'unlimited' if rps == 0 else rps}"
        summary = await tester.run_test(
            args.endpoint,
            args.requests,
            concurrency,
            rps,
            args.timeout
        )
        tester.print_summary(summary, test_name)
    else:
        # Run multiple tests with different combinations
        summaries = []
        
        for concurrency in args.concurrency:
            for rps in args.rps:
                test_name = f"Concurrency={concurrency}, RPS={'unlimited' if rps == 0 else rps}"
                print(f"\nRunning: {test_name}")
                
                summary = await tester.run_test(
                    args.endpoint,
                    args.requests,
                    concurrency,
                    rps,
                    args.timeout
                )
                
                tester.print_summary(summary, test_name)
                summaries.append((test_name, summary))
                
                # Small delay between tests to avoid overwhelming the API
                await asyncio.sleep(2)
        
        # Print comparison table
        print("\n" + "=" * 80)
        print("COMPARISON SUMMARY")
        print("=" * 80)
        print(f"{'Test':<40} {'Success %':<12} {'Avg RT (s)':<12} {'RPS':<12}")
        print("-" * 80)
        for test_name, summary in summaries:
            success_pct = (summary.successful_requests / summary.total_requests * 100) if summary.total_requests > 0 else 0
            print(f"{test_name:<40} {success_pct:>10.1f}%  {summary.avg_response_time:>10.3f}  {summary.requests_per_second:>10.2f}")


if __name__ == "__main__":
    asyncio.run(main())
