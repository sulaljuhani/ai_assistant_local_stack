# Code Review Report - AI Assistant Local Stack
**Date:** 2025-11-19
**Reviewer:** Claude (Automated Code Review)
**Codebase Version:** claude/codebase-review-01G2yhApw5jpuE3X68Y1Ay9t

---

## Executive Summary

This comprehensive code review analyzed the AI Assistant Local Stack codebase, encompassing:
- **4,435 lines** of Python code
- **2,494 lines** of Bash scripts
- **16,822 lines** of documentation
- **10 SQL migrations** defining 18 database tables
- **18 n8n workflow** configurations
- **2 Docker containers** (MCP Server, LangGraph Agents)

### Overall Assessment: ⚠️ NEEDS ATTENTION

**Strengths:**
- Well-structured codebase with clear separation of concerns
- Comprehensive documentation
- Good use of async/await patterns
- Proper logging infrastructure
- Type hints present in most code

**Critical Issues Found:**
- **5 SQL injection vulnerabilities** (HIGH SEVERITY)
- **1 CORS misconfiguration** (MEDIUM SEVERITY)
- **Missing input validation** in multiple locations
- **Hardcoded secrets** in some areas
- **No retry logic** in database connection for LangGraph agents

---

## Table of Contents

1. [Security Issues](#1-security-issues)
2. [Code Quality](#2-code-quality)
3. [Architecture & Design](#3-architecture--design)
4. [Error Handling & Logging](#4-error-handling--logging)
5. [Database & Migrations](#5-database--migrations)
6. [Testing](#6-testing)
7. [Dependencies](#7-dependencies)
8. [Docker & Deployment](#8-docker--deployment)
9. [Configuration Management](#9-configuration-management)
10. [Performance](#10-performance)
11. [Recommendations](#11-recommendations)

---

## 1. Security Issues

### 🔴 CRITICAL: SQL Injection Vulnerabilities

**Location:** `containers/langgraph-agents/tools/database.py`

**Issue:** Multiple instances of string interpolation in SQL queries allowing SQL injection attacks.

**Affected Lines:**
- Line 54: `query += f" AND logged_at >= NOW() - INTERVAL '{days_ago} days'"`
- Line 66: `query += f" ORDER BY logged_at DESC LIMIT {limit}"`
- Line 246: `.format(days=days_ago)` in food pattern analysis
- Line 304: `query += f" ORDER BY priority DESC, due_date ASC LIMIT {limit}"`
- Line 468: `.format(days=days, limit=limit)` in tasks due soon

**Example Vulnerable Code:**
```python
# VULNERABLE - Line 54
if days_ago:
    param_count += 1
    query += f" AND logged_at >= NOW() - INTERVAL '{days_ago} days'"
    # days_ago is directly interpolated, not parameterized!
```

**Attack Vector:**
```python
# Attacker could pass:
days_ago = "1 days'; DROP TABLE food_log; --"
# Resulting query would execute arbitrary SQL
```

**Impact:** HIGH - Complete database compromise, data loss, unauthorized access

**Recommendation:**
```python
# SECURE VERSION
if days_ago:
    param_count += 1
    params.append(days_ago)
    query += f" AND logged_at >= NOW() - INTERVAL '1 day' * ${param_count}"
```

**Files to Fix:**
- `containers/langgraph-agents/tools/database.py` (5 instances)

---

### 🟡 MEDIUM: CORS Misconfiguration

**Location:** `containers/langgraph-agents/main.py:62-68`

**Issue:** CORS middleware allows ALL origins (`allow_origins=["*"]`)

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ INSECURE
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Impact:** MEDIUM - Allows any website to make authenticated requests to your API

**Recommendation:**
```python
# Use environment variable for allowed origins
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3001").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)
```

---

### 🟡 MEDIUM: Hardcoded Default Password

**Location:** Multiple files

**Issue:** Default passwords in code instead of requiring environment variables

**Affected Files:**
- `containers/mcp-server/server.py:86` - `"password": os.getenv("POSTGRES_PASSWORD", "changeme")`
- `scripts/python/deduplicate_memories.py:29` - Same issue

**Recommendation:**
```python
# Fail fast if password not set
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
if not POSTGRES_PASSWORD:
    raise ValueError("POSTGRES_PASSWORD environment variable must be set")

DB_CONFIG = {
    "password": POSTGRES_PASSWORD,
    # ...
}
```

---

### 🟡 MEDIUM: Missing Input Validation

**Location:** Multiple tool functions

**Issues:**
1. No validation on `days_ago`, `limit` parameters (could be negative, extremely large)
2. No sanitization of string inputs
3. No rate limiting on API endpoints

**Example - Unvalidated Input:**
```python
@tool
async def search_food_log(
    user_id: str,
    days_ago: Optional[int] = 7,  # No validation - could be -1000 or 999999
    min_rating: Optional[int] = None,  # No validation - could be 100
    limit: int = 20  # No validation
):
```

**Recommendation:**
```python
@tool
async def search_food_log(
    user_id: str,
    days_ago: Optional[int] = 7,
    min_rating: Optional[int] = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    # Validate inputs
    if days_ago is not None and (days_ago < 1 or days_ago > 365):
        raise ValueError("days_ago must be between 1 and 365")

    if min_rating is not None and (min_rating < 1 or min_rating > 5):
        raise ValueError("min_rating must be between 1 and 5")

    if limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100")

    # ... rest of function
```

---

### 🟢 LOW: Secrets in Environment Variables

**Location:** `.env.example`

**Issue:** While `.env.example` correctly shows template, actual `.env` file handling not validated

**Recommendation:**
- Add `.env` to `.gitignore` (verify this exists)
- Add secret rotation documentation
- Consider using a secrets manager (HashiCorp Vault, AWS Secrets Manager) for production

---

## 2. Code Quality

### ✅ Strengths

1. **Good Module Organization**
   - Clear separation: agents, tools, utils, graph
   - Logical file naming conventions

2. **Type Hints Present**
   - Most functions have type annotations
   - Good use of `Optional`, `List`, `Dict`, `Any`

3. **Docstrings**
   - Module-level docstrings present
   - Function docstrings with parameter descriptions

4. **Code Formatting**
   - Consistent indentation
   - `black` formatter included in dependencies

### ⚠️ Issues

#### Missing Detailed Docstrings

**Location:** Multiple files

**Issue:** Some functions lack complete parameter and return type documentation

**Example:**
```python
# BEFORE
async def get_db_pool() -> asyncpg.Pool:
    """Get or create database connection pool."""
```

**Recommendation:**
```python
# AFTER
async def get_db_pool() -> asyncpg.Pool:
    """
    Get or create database connection pool.

    Creates a new connection pool on first call, then returns the cached pool
    on subsequent calls. Pool configuration is read from settings.

    Returns:
        asyncpg.Pool: PostgreSQL connection pool (min 2, max 10 connections)

    Raises:
        asyncpg.PostgresError: If unable to connect to database

    Example:
        >>> pool = await get_db_pool()
        >>> async with pool.acquire() as conn:
        ...     result = await conn.fetchrow("SELECT 1")
    """
```

#### Magic Numbers

**Locations:**
- `containers/langgraph-agents/utils/db.py:33-34` - Pool sizes (2, 10)
- `containers/mcp-server/server.py:120-121` - Pool sizes
- `containers/mcp-server/server.py:112-113` - Retry logic (3, 2)

**Recommendation:**
```python
# Define constants at module level
DEFAULT_MIN_POOL_SIZE = 2
DEFAULT_MAX_POOL_SIZE = 10
DB_CONNECTION_MAX_RETRIES = 3
DB_CONNECTION_RETRY_DELAY = 2  # seconds
```

#### Lambda Functions in Tool Map

**Location:** `containers/mcp-server/server.py:590-603`

**Issue:** Lambda functions make debugging harder and reduce code readability

**Current:**
```python
tool_map = {
    "get_reminders_today": lambda: get_reminders_today(),
    "search_reminders": lambda: search_reminders(arguments["query"]),
}
```

**Recommendation:**
```python
# Direct function references with argument handling
async def execute_tool(name: str, arguments: dict) -> str:
    if name == "get_reminders_today":
        return await get_reminders_today()
    elif name == "search_reminders":
        return await search_reminders(arguments["query"])
    # ...
    else:
        raise ValueError(f"Unknown tool: {name}")
```

---

## 3. Architecture & Design

### ✅ Strengths

1. **Multi-Agent Architecture** - Clean separation of concerns
2. **LangGraph Integration** - Proper state management and checkpointing
3. **Async/Await** - Proper async patterns throughout
4. **Connection Pooling** - Good database connection management

### ⚠️ Issues

#### No Retry Logic in LangGraph DB Connection

**Location:** `containers/langgraph-agents/utils/db.py:16-39`

**Issue:** Unlike MCP server which has retry logic, LangGraph DB connection has none

**MCP Server (GOOD):**
```python
# containers/mcp-server/server.py:104-138
async def get_db_pool() -> asyncpg.Pool:
    # ... has retry logic with exponential backoff
    for attempt in range(max_retries):
        try:
            # ... connection attempt
        except Exception as e:
            # ... retry with backoff
```

**LangGraph (BAD):**
```python
# containers/langgraph-agents/utils/db.py:16-39
async def get_db_pool() -> asyncpg.Pool:
    # No retry logic - fails immediately on error
    if _db_pool is None:
        _db_pool = await asyncpg.create_pool(...)  # ⚠️ No retries
```

**Recommendation:** Apply same retry pattern from MCP server

---

#### Inconsistent Error Responses

**Location:** `containers/langgraph-agents/tools/database.py`

**Issue:** Some functions return `{"error": str(e)}`, others return `[]`

```python
# Line 75-76 - Returns empty list
except Exception as e:
    logger.error(f"Error searching food log: {e}")
    return []  # ⚠️ Silent failure

# Line 122-124 - Returns error dict
except Exception as e:
    logger.error(f"Error logging food: {e}")
    return {"error": str(e)}  # ⚠️ Different error handling
```

**Recommendation:** Standardize error handling
```python
class ToolError(Exception):
    """Base exception for tool errors."""
    pass

# Let exceptions propagate, handle at agent level
# OR use consistent Result type:
from typing import Union

ToolResult = Union[List[Dict], Dict[str, str]]  # Success or {"error": "..."}
```

---

## 4. Error Handling & Logging

### ✅ Strengths

1. **Structured JSON Logging** in MCP server
2. **Exception Logging** with `exc_info=True`
3. **Specific Exception Types** (asyncpg.PostgresError, ConnectionError, etc.)

### ⚠️ Issues

#### Inconsistent Logging Format

**MCP Server:** JSON structured logging
```python
class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            # ...
        })
```

**LangGraph Agents:** Simple text logging
```python
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    # ...
)
```

**Recommendation:** Standardize on JSON logging for production observability

#### Missing Correlation IDs

**Issue:** No request correlation IDs for tracing requests across services

**Recommendation:**
```python
import uuid

@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))

    # Add to logger context
    with logger.contextualize(correlation_id=correlation_id):
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response
```

---

## 5. Database & Migrations

### ✅ Strengths

1. **Well-Organized Migrations** - Numbered, logical progression
2. **Proper Indexes** - Performance indexes defined
3. **Foreign Keys** - Referential integrity maintained
4. **Trigger Functions** - Auto-update `updated_at` columns

### ⚠️ Issues

#### No Rollback Scripts

**Location:** `migrations/` directory

**Issue:** Only forward migrations exist, no rollback/down migrations

**Recommendation:** Create paired migration files:
- `001_initial_schema_up.sql`
- `001_initial_schema_down.sql`

#### No Migration Tracking Table

**Issue:** No system to track which migrations have been applied

**Recommendation:** Use migration tool like `alembic` or create tracking:
```sql
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TIMESTAMP DEFAULT NOW()
);
```

---

## 6. Testing

### ✅ Strengths

1. **Test Infrastructure** - Webhook test script exists
2. **Test Framework** - pytest and pytest-asyncio in requirements

### ⚠️ Issues

#### Limited Test Coverage

**Location:** `tests/` directory

**Current State:**
- Manual webhook testing script
- No unit tests for Python code
- No integration tests
- No test fixtures

**Test Files Missing:**
- `tests/test_mcp_server.py`
- `tests/test_agents.py`
- `tests/test_tools.py`
- `tests/test_database.py`

**Recommendation:**

Create comprehensive test suite:

```python
# tests/test_tools.py
import pytest
from containers.langgraph_agents.tools.database import search_food_log

@pytest.mark.asyncio
async def test_search_food_log_validation():
    """Test input validation for search_food_log."""

    # Test invalid days_ago
    with pytest.raises(ValueError, match="days_ago must be"):
        await search_food_log(
            user_id="test",
            days_ago=-1  # Invalid
        )

    # Test invalid rating
    with pytest.raises(ValueError, match="min_rating must be"):
        await search_food_log(
            user_id="test",
            min_rating=10  # Invalid
        )

@pytest.mark.asyncio
async def test_search_food_log_sql_injection():
    """Test SQL injection protection."""

    # Should NOT execute SQL injection
    result = await search_food_log(
        user_id="test",
        days_ago="1'; DROP TABLE food_log; --"
    )
    # After fixing SQL injection, this should raise ValueError or be parameterized
```

**Coverage Target:** Aim for 80%+ code coverage

---

## 7. Dependencies

### ✅ Strengths

1. **Modern Versions** - Recent versions of most packages
2. **Development Tools** - pytest, black included

### ⚠️ Issues

#### Unpinned Minor Versions

**Location:** `containers/langgraph-agents/requirements.txt`

**Issue:** Some packages allow minor version changes

```txt
langgraph==0.2.50  # ✅ Good - fully pinned
langchain==0.3.7   # ✅ Good
fastapi==0.115.0   # ✅ Good
```

**Recommendation:** All versions are already pinned - this is good! Just maintain this practice.

#### Missing Security Scanning

**Recommendation:** Add dependency vulnerability scanning

```bash
# Add to CI/CD pipeline
pip install safety
safety check --json

# Or use dependabot in GitHub
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/containers/langgraph-agents"
    schedule:
      interval: "weekly"
```

---

## 8. Docker & Deployment

### ✅ Strengths

1. **Health Checks** - Dockerfile includes HEALTHCHECK
2. **Multi-Stage Potential** - Room for optimization
3. **Slim Base Image** - Using python:3.11-slim

### ⚠️ Issues

#### Running as Root

**Location:** All Dockerfiles

**Issue:** Containers run as root user

**Current:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
# ... no USER directive
CMD ["python", "main.py"]  # Runs as root
```

**Recommendation:**
```dockerfile
FROM python:3.11-slim

# Create non-root user
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Install dependencies as root
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app and change ownership
COPY . .
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Run as non-root
CMD ["python", "main.py"]
```

#### No Multi-Stage Build

**Issue:** Build tools (gcc, g++) included in final image

**Recommendation:**
```dockerfile
# Stage 1: Builder
FROM python:3.11-slim AS builder
WORKDIR /app
RUN apt-get update && apt-get install -y gcc g++
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim
WORKDIR /app
RUN useradd -m -u 1000 appuser

# Copy only necessary files from builder
COPY --from=builder /root/.local /home/appuser/.local
COPY --chown=appuser:appuser . .

USER appuser
ENV PATH=/home/appuser/.local/bin:$PATH
CMD ["python", "main.py"]
```

**Benefits:**
- Smaller image size (remove build tools)
- Improved security (no compilation tools in runtime)

---

## 9. Configuration Management

### ✅ Strengths

1. **Environment Variables** - Good use of .env files
2. **Pydantic Settings** - Type-safe configuration in LangGraph agents
3. **Example File** - Comprehensive .env.example

### ⚠️ Issues

#### Secrets in Code Comments

**Location:** `.env.example`

**Issue:** While example file is good, no validation that production doesn't use defaults

**Recommendation:**

Add startup validation:

```python
# containers/langgraph-agents/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    postgres_password: str

    @validator('postgres_password')
    def validate_not_default(cls, v):
        """Prevent using default/weak passwords in production."""
        if v in ['changeme', 'password', 'admin', '']:
            raise ValueError(
                "Default password detected! Set POSTGRES_PASSWORD to a strong value."
            )
        if len(v) < 16:
            raise ValueError("Password must be at least 16 characters")
        return v
```

#### No Environment Detection

**Issue:** No differentiation between dev/staging/prod

**Recommendation:**
```python
class Settings(BaseSettings):
    environment: str = "development"  # development, staging, production

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

# Use in code:
if settings.is_production and not settings.postgres_password:
    raise ValueError("POSTGRES_PASSWORD required in production")
```

---

## 10. Performance

### ✅ Strengths

1. **Connection Pooling** - Async connection pools used
2. **Database Indexes** - Performance indexes defined
3. **Async I/O** - Non-blocking operations

### ⚠️ Issues

#### No Query Result Caching

**Location:** MCP server and LangGraph tools

**Issue:** Frequently accessed data (categories, summaries) not cached

**Example - Repeatedly Queried:**
```python
async def get_reminder_categories():
    # Categories rarely change but queried often
    # No caching implemented
    rows = await conn.fetch("SELECT ...")
```

**Recommendation:**
```python
from functools import lru_cache
import asyncio

# For static/rarely changing data
@lru_cache(maxsize=128)
async def get_reminder_categories_cached(ttl: int = 300):
    # Cache for 5 minutes
    return await get_reminder_categories()

# Or use Redis caching:
async def get_reminder_categories():
    cache_key = f"categories:{user_id}"

    # Try cache first
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    # Query database
    result = await conn.fetch(...)

    # Store in cache (5 minute TTL)
    await redis_client.setex(cache_key, 300, json.dumps(result))

    return result
```

#### N+1 Query Pattern

**Location:** Potential issue in agents when fetching related data

**Recommendation:** Use JOIN queries instead of multiple queries in loops

```python
# BAD - N+1 queries
tasks = await get_all_tasks(user_id)
for task in tasks:
    category = await get_category(task.category_id)  # N queries!

# GOOD - Single JOIN query
tasks_with_categories = await conn.fetch("""
    SELECT t.*, c.name as category_name
    FROM tasks t
    LEFT JOIN categories c ON t.category_id = c.id
    WHERE t.user_id = $1
""", user_id)
```

#### No Request Rate Limiting

**Location:** FastAPI endpoints

**Recommendation:**
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/chat")
@limiter.limit("10/minute")  # 10 requests per minute
async def chat(request: Request, req: ChatRequest):
    # ...
```

---

## 11. Recommendations

### 🔴 CRITICAL (Fix Immediately)

1. **Fix SQL Injection Vulnerabilities**
   - Priority: URGENT
   - Effort: 2-4 hours
   - Files: `containers/langgraph-agents/tools/database.py`
   - Impact: Prevents database compromise

2. **Restrict CORS Origins**
   - Priority: HIGH
   - Effort: 30 minutes
   - Files: `containers/langgraph-agents/main.py`
   - Impact: Prevents unauthorized API access

3. **Remove Default Passwords**
   - Priority: HIGH
   - Effort: 1 hour
   - Files: `containers/mcp-server/server.py`, scripts
   - Impact: Forces secure password configuration

### 🟡 HIGH PRIORITY (Fix in Next Sprint)

4. **Add Input Validation**
   - Priority: HIGH
   - Effort: 4-6 hours
   - Impact: Prevents invalid data and potential exploits

5. **Implement Retry Logic in LangGraph DB**
   - Priority: MEDIUM-HIGH
   - Effort: 1-2 hours
   - Impact: Improves reliability

6. **Add Unit Tests**
   - Priority: MEDIUM-HIGH
   - Effort: 8-16 hours
   - Impact: Catches bugs early, enables refactoring

7. **Run Containers as Non-Root**
   - Priority: MEDIUM
   - Effort: 2-3 hours
   - Impact: Improves security posture

### 🟢 NICE TO HAVE (Future Improvements)

8. **Add Migration Rollback Scripts**
   - Priority: MEDIUM
   - Effort: 4-6 hours
   - Impact: Enables safer deployments

9. **Implement Caching Strategy**
   - Priority: MEDIUM
   - Effort: 6-8 hours
   - Impact: Improves performance

10. **Standardize Error Handling**
    - Priority: LOW-MEDIUM
    - Effort: 4-6 hours
    - Impact: Consistent error responses

11. **Add Correlation IDs**
    - Priority: LOW-MEDIUM
    - Effort: 2-3 hours
    - Impact: Better observability

12. **Implement Rate Limiting**
    - Priority: LOW
    - Effort: 2-3 hours
    - Impact: Prevents abuse

---

## Summary Metrics

| Category | Score | Details |
|----------|-------|---------|
| **Security** | ⚠️ 4/10 | Critical SQL injection issues |
| **Code Quality** | ✅ 7/10 | Good structure, minor improvements needed |
| **Testing** | ⚠️ 3/10 | Limited test coverage |
| **Documentation** | ✅ 8/10 | Comprehensive docs, minor gaps |
| **Performance** | ✅ 7/10 | Good async patterns, caching opportunities |
| **Deployment** | ✅ 6/10 | Works but security improvements needed |

### Overall Score: 6/10

**Bottom Line:** The codebase is well-architected and functional, but has critical security vulnerabilities that must be addressed before production deployment. Once the SQL injection and CORS issues are fixed, and input validation is added, this would be a solid 8/10 codebase.

---

## Action Plan (Prioritized)

### Week 1 (CRITICAL)
- [ ] Fix all 5 SQL injection vulnerabilities
- [ ] Add parameterized query helper function
- [ ] Update CORS to whitelist specific origins
- [ ] Add startup validation for passwords

### Week 2 (HIGH PRIORITY)
- [ ] Add input validation to all tool functions
- [ ] Implement retry logic in LangGraph DB connection
- [ ] Add non-root user to Dockerfiles
- [ ] Write unit tests for database tools (target 50% coverage)

### Week 3 (IMPROVEMENTS)
- [ ] Standardize error handling across tools
- [ ] Add correlation IDs to requests
- [ ] Implement basic caching for categories/summaries
- [ ] Add rate limiting to API endpoints

### Week 4 (POLISH)
- [ ] Create migration rollback scripts
- [ ] Add multi-stage Docker builds
- [ ] Increase test coverage to 80%
- [ ] Add dependency vulnerability scanning to CI/CD

---

## Appendix: Code Examples

### A. Secure SQL Query Helper

```python
# containers/langgraph-agents/utils/query_builder.py
from typing import List, Any, Tuple

class QueryBuilder:
    """Helper for building parameterized SQL queries safely."""

    def __init__(self, base_query: str):
        self.query = base_query
        self.params: List[Any] = []
        self.param_count = 0

    def add_param(self, value: Any) -> str:
        """Add a parameter and return its placeholder."""
        self.param_count += 1
        self.params.append(value)
        return f"${self.param_count}"

    def add_filter(self, condition: str, value: Any) -> None:
        """Add a WHERE condition with parameter."""
        placeholder = self.add_param(value)
        if "WHERE" not in self.query.upper():
            self.query += f" WHERE {condition.replace('?', placeholder)}"
        else:
            self.query += f" AND {condition.replace('?', placeholder)}"

    def add_limit(self, limit: int) -> None:
        """Add LIMIT clause safely."""
        # Validate limit
        if not isinstance(limit, int) or limit < 1 or limit > 1000:
            raise ValueError("Limit must be integer between 1 and 1000")
        self.query += f" LIMIT {limit}"  # Safe - validated integer

    def build(self) -> Tuple[str, List[Any]]:
        """Return query and parameters."""
        return self.query, self.params

# Usage:
qb = QueryBuilder("SELECT * FROM food_log")
qb.add_filter("user_id = ?", user_id)
if days_ago:
    qb.add_filter("logged_at >= NOW() - INTERVAL '1 day' * ?", days_ago)
qb.add_limit(limit)

query, params = qb.build()
rows = await conn.fetch(query, *params)
```

### B. Input Validation Decorator

```python
# containers/langgraph-agents/utils/validation.py
from functools import wraps
from typing import Callable, Any

def validate_inputs(**validators):
    """
    Decorator to validate function inputs.

    Usage:
        @validate_inputs(
            days_ago=lambda x: 1 <= x <= 365,
            rating=lambda x: x is None or 1 <= x <= 5
        )
        async def my_function(days_ago: int, rating: Optional[int]):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            import inspect
            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()

            for param_name, validator in validators.items():
                if param_name in bound.arguments:
                    value = bound.arguments[param_name]
                    if value is not None and not validator(value):
                        raise ValueError(
                            f"Invalid value for {param_name}: {value}"
                        )

            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

---

**End of Report**

For questions or clarifications, please refer to the specific line numbers and file paths mentioned throughout this report.
