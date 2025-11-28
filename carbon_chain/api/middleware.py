"""
CarbonChain - API Middleware
==============================
Custom middleware for FastAPI application.
"""

import time
import uuid
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp

from carbon_chain.logging_setup import get_logger

logger = get_logger("api.middleware")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Add unique request ID to each request.
    
    Useful for tracking requests in logs and debugging.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        # Add to request state
        request.state.request_id = request_id
        
        # Process request
        response = await call_next(request)
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Log all API requests with timing information.
    
    Logs:
    - Request method and path
    - Response status code
    - Request duration
    - Client IP
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Start timer
        start_time = time.time()
        
        # Get request ID if available
        request_id = getattr(request.state, "request_id", "unknown")
        
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Log request
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} "
            f"from {client_ip}"
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log response
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} "
            f"-> {response.status_code} ({duration:.3f}s)"
        )
        
        # Add timing header
        response.headers["X-Process-Time"] = str(duration)
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware.
    
    Implements token bucket algorithm for rate limiting.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        requests_per_minute: int = 60,
        burst_size: int = 10
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.buckets = {}  # IP -> (tokens, last_update)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/", "/docs", "/openapi.json"]:
            return await call_next(request)
        
        # Check rate limit
        if not self._check_rate_limit(client_ip):
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too Many Requests",
                    "detail": f"Rate limit: {self.requests_per_minute} requests/minute"
                },
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": "0"
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = self._get_remaining_tokens(client_ip)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        
        return response
    
    def _check_rate_limit(self, client_ip: str) -> bool:
        """Check if client is within rate limit"""
        now = time.time()
        
        if client_ip not in self.buckets:
            # New client - give full burst
            self.buckets[client_ip] = (self.burst_size - 1, now)
            return True
        
        tokens, last_update = self.buckets[client_ip]
        
        # Calculate tokens to add based on time passed
        time_passed = now - last_update
        tokens_to_add = time_passed * (self.requests_per_minute / 60)
        
        # Update tokens (cap at burst size)
        tokens = min(self.burst_size, tokens + tokens_to_add)
        
        # Check if we have tokens
        if tokens >= 1:
            self.buckets[client_ip] = (tokens - 1, now)
            return True
        else:
            self.buckets[client_ip] = (tokens, now)
            return False
    
    def _get_remaining_tokens(self, client_ip: str) -> int:
        """Get remaining tokens for client"""
        if client_ip not in self.buckets:
            return self.burst_size
        
        tokens, _ = self.buckets[client_ip]
        return int(tokens)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Global error handling middleware.
    
    Catches unhandled exceptions and returns proper error responses.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response
        
        except Exception as e:
            # Log error
            request_id = getattr(request.state, "request_id", "unknown")
            logger.error(
                f"[{request_id}] Unhandled error: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            
            # Return error response
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "detail": "An unexpected error occurred",
                    "request_id": request_id
                }
            )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses.
    
    Headers:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Strict-Transport-Security (HTTPS only)
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Add HSTS if HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = \
                "max-age=31536000; includeSubDomains"
        
        return response


class CompressionMiddleware(BaseHTTPMiddleware):
    """
    Enable response compression for large payloads.
    
    Compresses responses > 1KB using gzip.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Check if client accepts gzip
        accept_encoding = request.headers.get("accept-encoding", "")
        if "gzip" not in accept_encoding.lower():
            return response
        
        # Check if response is already compressed
        if response.headers.get("content-encoding"):
            return response
        
        # Check content type (only compress text/json)
        content_type = response.headers.get("content-type", "")
        if not any(t in content_type for t in ["text", "json", "javascript"]):
            return response
        
        # TODO: Implement actual gzip compression
        # For now, just return original response
        # In production, use middleware like fastapi-gzip
        
        return response


class CacheControlMiddleware(BaseHTTPMiddleware):
    """
    Add cache control headers to responses.
    
    Different caching strategies for different endpoints:
    - Blockchain data: Cache for 10 seconds (blocks don't change)
    - Dynamic data: No cache
    - Static files: Cache for 1 year
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        path = request.url.path
        
        # Static files - long cache
        if path.startswith("/static/"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        
        # Block data - short cache
        elif "/block/" in path or "/blockchain/" in path:
            response.headers["Cache-Control"] = "public, max-age=10"
        
        # Transaction data - no cache (might be pending)
        elif "/transaction/" in path or "/mempool/" in path:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        
        # Address data - no cache (balances change)
        elif "/address/" in path:
            response.headers["Cache-Control"] = "no-cache, max-age=0"
        
        # Default - no cache
        else:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        
        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Collect API metrics.
    
    Tracks:
    - Request count by endpoint
    - Response time by endpoint
    - Error rate
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.metrics = {
            "requests": {},
            "errors": {},
            "response_times": {}
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        method = request.method
        key = f"{method} {path}"
        
        # Start timer
        start_time = time.time()
        
        # Process request
        try:
            response = await call_next(request)
            
            # Record metrics
            self._record_request(key)
            self._record_response_time(key, time.time() - start_time)
            
            if response.status_code >= 400:
                self._record_error(key, response.status_code)
            
            return response
        
        except Exception as e:
            # Record error
            self._record_error(key, 500)
            raise
    
    def _record_request(self, key: str):
        """Record request count"""
        self.metrics["requests"][key] = self.metrics["requests"].get(key, 0) + 1
    
    def _record_error(self, key: str, status_code: int):
        """Record error"""
        error_key = f"{key}:{status_code}"
        self.metrics["errors"][error_key] = self.metrics["errors"].get(error_key, 0) + 1
    
    def _record_response_time(self, key: str, duration: float):
        """Record response time"""
        if key not in self.metrics["response_times"]:
            self.metrics["response_times"][key] = []
        
        # Keep last 100 measurements
        times = self.metrics["response_times"][key]
        times.append(duration)
        if len(times) > 100:
            times.pop(0)
    
    def get_metrics(self) -> dict:
        """Get current metrics"""
        return {
            "requests": dict(self.metrics["requests"]),
            "errors": dict(self.metrics["errors"]),
            "avg_response_time": {
                k: sum(v) / len(v) if v else 0
                for k, v in self.metrics["response_times"].items()
            }
        }


def setup_cors_middleware(app: ASGIApp) -> CORSMiddleware:
    """
    Setup CORS middleware.
    
    Allows cross-origin requests for API access.
    """
    return CORSMiddleware(
        app,
        allow_origins=["*"],  # In production, restrict to specific domains
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Process-Time", "X-RateLimit-Limit", "X-RateLimit-Remaining"]
    )


__all__ = [
    'RequestIDMiddleware',
    'RequestLoggingMiddleware',
    'RateLimitMiddleware',
    'ErrorHandlingMiddleware',
    'SecurityHeadersMiddleware',
    'CompressionMiddleware',
    'CacheControlMiddleware',
    'MetricsMiddleware',
    'setup_cors_middleware',
]
