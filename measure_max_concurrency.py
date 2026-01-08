#!/usr/bin/env python3
"""
Measure Maximum Concurrency Limit for CourtListener API

This script tests increasing concurrency levels to find the maximum
concurrency that the API can handle before failures occur.
"""

import os
import time
import asyncio
import aiohttp
import argparse
from datetime import datetime
from typing import List, Dict
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class ConcurrencyTestResult:
    """Results from a concurrency level test"""
    concurrency: int
    total_requests: int
    successful: int
    failed: int
    success_rate: float
    avg_response_time: float
    duration: float
    requests_per_second: float
    status_codes: Dict[int, int]
    errors: Dict[str, int]

class CourtListenerConcurrencyTester:
    """Tests CourtListener API to find maximum concurrency limit"""
    
    BASE_URL = "https://www.courtlistener.com/api/rest/v4"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Token {api_key}",
            "Content-Type": "application/json"
        }
    
    async def make_request(self, session: aiohttp.ClientSession, endpoint: str) -> tuple:
        """Make a single API request and return status and response time"""
        start_time = time.time()
        try:
            url = f"{self.BASE_URL}/{endpoint}"
            async with session.get(url, headers=self.headers) as response:
                status_code = response.status
                response_time = time.time() - start_time
                success = 200 <= status_code < 300
                
                error_msg = ""
                if not success:
                    try:
                        response_text = await response.text()
                        import json
                        error_data = json.loads(response_text)
                        if 'detail' in error_data:
                            error_msg = error_data['detail']
                        elif 'message' in error_data:
                            error_msg = error_data['message']
                        else:
                            error_msg = response_text[:100] if response_text else "No response body"
                    except:
                        error_msg = f"HTTP {status_code}"
                
                return (status_code, response_time, success, error_msg)
        except asyncio.TimeoutError:
            return (0, time.time() - start_time, False, "Timeout")
        except Exception as e:
            return (0, time.time() - start_time, False, f"{type(e).__name__}: {str(e)}")
    
    async def test_concurrency(
        self,
        endpoint: str,
        num_requests: int,
        concurrency: int,
        timeout: int = 30
    ) -> ConcurrencyTestResult:
        """Test a specific concurrency level"""
        results = []
        status_codes = {}
        errors = {}
        response_times = []
        
        semaphore = asyncio.Semaphore(concurrency)
        timeout_config = aiohttp.ClientTimeout(total=timeout)
        
        start_time = time.time()
        
        async with aiohttp.ClientSession(timeout=timeout_config) as session:
            async def make_request_with_semaphore():
                async with semaphore:
                    status, rt, success, error = await self.make_request(session, endpoint)
                    results.append((status, rt, success, error))
                    if success:
                        response_times.append(rt)
            
            tasks = [make_request_with_semaphore() for _ in range(num_requests)]
            await asyncio.gather(*tasks)
        
        duration = time.time() - start_time
        
        # Analyze results
        successful = sum(1 for _, _, success, _ in results if success)
        failed = num_requests - successful
        success_rate = (successful / num_requests * 100) if num_requests > 0 else 0
        
        for status, _, _, _ in results:
            status_codes[status] = status_codes.get(status, 0) + 1
        
        for _, _, _, error in results:
            if error:
                errors[error] = errors.get(error, 0) + 1
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        rps = num_requests / duration if duration > 0 else 0
        
        return ConcurrencyTestResult(
            concurrency=concurrency,
            total_requests=num_requests,
            successful=successful,
            failed=failed,
            success_rate=success_rate,
            avg_response_time=avg_response_time,
            duration=duration,
            requests_per_second=rps,
            status_codes=status_codes,
            errors=errors
        )
    
    def print_result(self, result: ConcurrencyTestResult):
        """Print formatted test result"""
        print(f"\n{'='*80}")
        print(f"Concurrency Level: {result.concurrency}")
        print(f"{'='*80}")
        print(f"Total Requests:     {result.total_requests}")
        print(f"Successful:         {result.successful} ({result.success_rate:.1f}%)")
        print(f"Failed:             {result.failed} ({100-result.success_rate:.1f}%)")
        print(f"Avg Response Time:  {result.avg_response_time:.3f}s")
        print(f"Duration:           {result.duration:.2f}s")
        print(f"Requests/Second:    {result.requests_per_second:.2f}")
        print(f"Status Codes:       {dict(result.status_codes)}")
        if result.errors:
            print(f"Errors:")
            for error, count in sorted(result.errors.items(), key=lambda x: x[1], reverse=True):
                print(f"  {error}: {count}")
        print(f"{'='*80}")


async def find_max_concurrency(
    api_key: str,
    endpoint: str = "search/",
    requests_per_test: int = 100,
    start_concurrency: int = 1,
    max_concurrency: int = 10000,
    step_size: int = 1,
    success_threshold: float = 95.0,
    timeout: int = 30,
    verbose: bool = False
):
    """Find maximum concurrency by testing increasing levels"""
    tester = CourtListenerConcurrencyTester(api_key)
    
    print(f"CourtListener API Maximum Concurrency Test")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Endpoint: {endpoint}")
    print(f"Requests per test: {requests_per_test}")
    print(f"Success threshold: {success_threshold}%")
    print(f"Testing from {start_concurrency} to {max_concurrency} concurrency")
    print(f"{'='*80}")
    
    current_concurrency = start_concurrency
    last_successful_concurrency = None
    results_history = []
    
    # Binary search approach for efficiency
    low = start_concurrency
    high = max_concurrency
    best_concurrency = start_concurrency
    
    while low <= high:
        # Test midpoint
        current_concurrency = (low + high) // 2
        
        if verbose or current_concurrency == start_concurrency:
            print(f"\nTesting concurrency: {current_concurrency}...")
        
        result = await tester.test_concurrency(
            endpoint,
            requests_per_test,
            current_concurrency,
            timeout
        )
        
        results_history.append(result)
        
        if verbose:
            tester.print_result(result)
        
        # Check if this concurrency level is acceptable
        if result.success_rate >= success_threshold:
            best_concurrency = current_concurrency
            last_successful_concurrency = current_concurrency
            if verbose:
                print(f"✓ Concurrency {current_concurrency}: {result.success_rate:.1f}% success - ACCEPTABLE")
            # Try higher concurrency
            low = current_concurrency + 1
        else:
            if verbose:
                print(f"✗ Concurrency {current_concurrency}: {result.success_rate:.1f}% success - FAILED")
            # Try lower concurrency
            high = current_concurrency - 1
        
        # Small delay between tests to avoid overwhelming the API
        await asyncio.sleep(1)
    
    # Final verification test at the best concurrency
    print(f"\n{'='*80}")
    print(f"FINAL VERIFICATION TEST")
    print(f"{'='*80}")
    print(f"Testing best concurrency level: {best_concurrency}")
    
    final_result = await tester.test_concurrency(
        endpoint,
        requests_per_test * 2,  # Use more requests for final test
        best_concurrency,
        timeout
    )
    
    tester.print_result(final_result)
    
    # Summary
    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    print(f"Maximum Concurrency (>{success_threshold}% success): {best_concurrency}")
    print(f"Final Test Results:")
    print(f"  - Success Rate: {final_result.success_rate:.1f}%")
    print(f"  - Successful Requests: {final_result.successful}/{final_result.total_requests}")
    print(f"  - Average Response Time: {final_result.avg_response_time:.3f}s")
    print(f"  - Throughput: {final_result.requests_per_second:.2f} requests/second")
    print(f"{'='*80}")
    
    return best_concurrency, final_result, results_history


async def linear_search_max_concurrency(
    api_key: str,
    endpoint: str = "search/",
    requests_per_test: int = 50,
    start_concurrency: int = 1,
    max_concurrency: int = 1000,
    step_size: int = 10,
    success_threshold: float = 95.0,
    timeout: int = 30,
    stop_on_failure: bool = True
):
    """Linear search for maximum concurrency (tests each level sequentially)"""
    tester = CourtListenerConcurrencyTester(api_key)
    
    print(f"CourtListener API Maximum Concurrency Test (Linear Search)")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Endpoint: {endpoint}")
    print(f"Requests per test: {requests_per_test}")
    print(f"Success threshold: {success_threshold}%")
    print(f"Testing from {start_concurrency} to {max_concurrency} concurrency (step: {step_size})")
    print(f"{'='*80}")
    
    results_history = []
    max_successful_concurrency = None
    
    for concurrency in range(start_concurrency, max_concurrency + 1, step_size):
        print(f"\nTesting concurrency: {concurrency}...")
        
        result = await tester.test_concurrency(
            endpoint,
            requests_per_test,
            concurrency,
            timeout
        )
        
        results_history.append(result)
        tester.print_result(result)
        
        if result.success_rate >= success_threshold:
            max_successful_concurrency = concurrency
            print(f"✓ PASSED - Success rate: {result.success_rate:.1f}%")
        else:
            print(f"✗ FAILED - Success rate: {result.success_rate:.1f}%")
            if stop_on_failure:
                print(f"\nStopping at first failure (concurrency {concurrency})")
                break
        
        # Small delay between tests
        await asyncio.sleep(1)
    
    # Summary
    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    if max_successful_concurrency:
        print(f"Maximum Successful Concurrency: {max_successful_concurrency}")
        print(f"Last successful test had {results_history[-1].success_rate:.1f}% success rate")
    else:
        print(f"No concurrency level met the {success_threshold}% success threshold")
    print(f"{'='*80}")
    
    return max_successful_concurrency, results_history


async def main():
    parser = argparse.ArgumentParser(
        description="Measure maximum concurrency limit for CourtListener API"
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
        help="Number of requests per test (default: 100)"
    )
    parser.add_argument(
        "--start",
        type=int,
        default=1,
        help="Starting concurrency level (default: 1)"
    )
    parser.add_argument(
        "--max",
        type=int,
        default=10000,
        help="Maximum concurrency to test (default: 10000)"
    )
    parser.add_argument(
        "--step",
        type=int,
        default=10,
        help="Step size for linear search (default: 10)"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=95.0,
        help="Success rate threshold percentage (default: 95.0)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Request timeout in seconds (default: 30)"
    )
    parser.add_argument(
        "--method",
        type=str,
        choices=["binary", "linear"],
        default="binary",
        help="Search method: binary (fast) or linear (detailed) (default: binary)"
    )
    parser.add_argument(
        "--stop-on-failure",
        action="store_true",
        help="Stop linear search on first failure (default: False)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed results for each test"
    )
    
    args = parser.parse_args()
    
    # Get API key from environment
    api_key = os.getenv("COURTLISTENER_API_KEY")
    if not api_key:
        print("ERROR: COURTLISTENER_API_KEY not found in environment variables")
        print("Please create a .env file with COURTLISTENER_API_KEY=your_key")
        return
    
    if args.method == "binary":
        await find_max_concurrency(
            api_key,
            args.endpoint,
            args.requests,
            args.start,
            args.max,
            args.step,
            args.threshold,
            args.timeout,
            args.verbose
        )
    else:
        await linear_search_max_concurrency(
            api_key,
            args.endpoint,
            args.requests,
            args.start,
            args.max,
            args.step,
            args.threshold,
            args.timeout,
            args.stop_on_failure
        )


if __name__ == "__main__":
    asyncio.run(main())
