# Lab 2 – Create PostgreSQL-Powered APIs with SQLAlchemy

Welcome to Lab 2! In this lab, you'll level up from a simple API to a **real database-backed application**. You'll run PostgreSQL in a Docker container, use SQLAlchemy ORM to interact with the database through Python objects, manage schema changes with Alembic migrations, and build a complete CRUD API for user management.

<!-- ![alt text](archi_diagrams/Lab-2_high-level.drawio.svg) -->
![Lab-2_high-level](https://raw.githubusercontent.com/poridhiEng/lab-asset/main/FastAPI-Basics-Lab-assets/Lab-2/images/archi_diagrams/Lab-2_high-level.drawio.svg)

## Objectives
- Set up PostgreSQL database using Docker Compose
- Connect FastAPI to PostgreSQL using SQLAlchemy ORM
- Define database models (tables) as Python classes
- Create Pydantic schemas for request/response validation
- Implement full CRUD API for user management
- Use Alembic to manage database schema migrations
- Test API endpoints with multiple methods
- Understand database sessions and connection management

## Background

### Why Do We Need Databases?

In Lab 1, our API returned data directly from the code. But what happens when:
- The server restarts? All data is lost!
- Multiple users need to access the same data?
- You need to store millions of records?
- You need to search, filter, or analyze data?

**Databases** solve these problems by providing:
- **Persistent storage** - Data survives server restarts
- **Concurrent access** - Multiple users can read/write simultaneously
- **Query capabilities** - Search, filter, sort, aggregate data efficiently
- **Data integrity** - Enforce rules (unique emails, required fields, etc.)
- **Relationships** - Connect related data (users and their posts)

### What is PostgreSQL?

**PostgreSQL** (often called "Postgres") is one of the world's most advanced open-source relational databases.

**Relational Database** means data is organized in **tables** (like Excel spreadsheets):
```
users table:
┌────┬──────────────────────┬─────────────┐
│ id │ email                │ username    │
├────┼──────────────────────┼─────────────┤
│ 1  │ alice@example.com    │ alice       │
│ 2  │ bob@example.com      │ bob         │
│ 3  │ charlie@example.com  │ charlie     │
└────┴──────────────────────┴─────────────┘
```

**Why PostgreSQL?**
- **Reliable**: Battle-tested for over 30 years
- **Feature-rich**: Supports JSON, full-text search, geospatial data
- **Standards-compliant**: Follows SQL standards strictly
- **Open-source**: Free to use, large community
- **Scalable**: Handles small to massive datasets
- **Used by**: Instagram, Spotify, Reddit, Uber

### What is an ORM (SQLAlchemy)?

**ORM = Object-Relational Mapping**

Instead of writing raw SQL queries like this:
```sql
SELECT * FROM users WHERE id = 1;
INSERT INTO users (email, username) VALUES ('ada@example.com', 'ada');
```

An ORM lets you use Python objects:
```python
user = db.query(User).filter(User.id == 1).first()
new_user = User(email="ada@example.com", username="ada")
db.add(new_user)
```

**Benefits of using SQLAlchemy:**
- **Pythonic**: Work with objects instead of SQL strings
- **Type-safe**: Catch errors before runtime
- **Database-agnostic**: Switch from PostgreSQL to MySQL with minimal changes
- **Less error-prone**: ORM handles SQL escaping, preventing SQL injection
- **Relationships**: Easy to define and query related data
- **Migrations friendly**: Works seamlessly with Alembic

**SQLAlchemy Components:**

<!-- ![alt text](archi_diagrams/Lab-2_sql-alchemy-components.drawio.svg) -->
![Lab-2_sql-alchemy-components](https://raw.githubusercontent.com/poridhiEng/lab-asset/main/FastAPI-Basics-Lab-assets/Lab-2/images/archi_diagrams/Lab-2_sql-alchemy-components.drawio.svg)

**1. Declarative Base:**
- Parent class for all models
- Maintains registry of all tables
- Provides metadata about schema

**2. Engine:**
- Manages connection pool
- Handles database dialect
- Entry point to database

**3. SessionLocal:**
- Factory for creating sessions
- Configured with engine
- Settings: autocommit=False, autoflush=False

**4. Session:**
- Your "workspace" for database operations
- Tracks changes to objects
- Manages transactions (commit/rollback)

**5. Connection Pool:**
- Maintains pool of database connections
- Reuses connections for efficiency
- Handles connection timeout and recycling

**6. Models:**
- Python classes representing database tables

### Connection Pool Management

<!-- ![alt text](archi_diagrams/Lab-2_connection-pool-management_sql-alchemy.drawio.svg) -->
![Lab-2_connection-pool-management_sql-alchemy](https://raw.githubusercontent.com/poridhiEng/lab-asset/main/FastAPI-Basics-Lab-assets/Lab-2/images/archi_diagrams/Lab-2_connection-pool-management_sql-alchemy.drawio.svg)

**What is a Connection Pool?**

A connection pool is a cache of database connections maintained by SQLAlchemy's Engine. Instead of creating a new connection for every database request (which is slow and expensive), SQLAlchemy reuses existing connections from the pool.

**Why Connection Pooling Matters:**

Without connection pooling, every database operation would:
1. Establish a new TCP connection to PostgreSQL (~50-100ms)
2. Authenticate with username/password (~20-50ms)
3. Execute the query (~5-20ms)
4. Close the connection (~10-20ms)

**Total: 85-190ms per request**

With connection pooling:
1. Get existing connection from pool (~1ms)
2. Execute the query (~5-20ms)
3. Return connection to pool (~1ms)

**Total: 7-22ms per request (10-20x faster!)**

**How Connection Pool Works:**

When you create an Engine in `app/database.py`:

```python
engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True
)
```

SQLAlchemy automatically creates a connection pool with default settings:
- **pool_size=5**: Maintains 5 persistent connections
- **max_overflow=10**: Can create 10 additional temporary connections when needed
- **pool_timeout=30**: Wait up to 30 seconds for an available connection untill raising an error
- **pool_recycle=3600**: Recycle connections after 1 hour (prevents stale connections)

**Connection Pool Lifecycle:**

1. **Application Starts**
   - Engine created with connection pool
   - Pool is initially empty (connections created on demand)

2. **First Request Arrives**
   - `get_db()` dependency creates a Session
   - Session requests a connection from pool
   - Pool is empty, so it creates a new connection to PostgreSQL
   - Connection used for query
   - Connection returned to pool (not closed!)

3. **Second Request Arrives**
   - Session requests connection from pool
   - Pool has 1 available connection from previous request
   - Reuses existing connection (very fast!)
   - Connection returned to pool

4. **Pool Grows Over Time**
   - As more concurrent requests arrive, pool creates more connections
   - Pool grows up to `pool_size` (5 connections)
   - These 5 connections are permanent and always kept alive

5. **Traffic Spike (More than 5 concurrent requests)**
   - Pool is at max size (5 connections all in use)
   - 6th request needs a connection
   - Pool creates an overflow connection (temporary)
   - Can create up to `max_overflow` (10) additional connections
   - Total possible concurrent connections: pool_size + max_overflow = 15

6. **Overflow Connections Cleanup**
   - When request completes, overflow connection is closed
   - Only the core pool_size connections are kept persistent
   - This prevents connection leaks during traffic spikes

**Connection States:**

- **Available**: Connection is in the pool, ready to be used
- **In Use**: Connection is currently executing a query
- **Overflow**: Temporary connection created during high traffic (discarded after use)
- **Stale**: Connection that's been idle too long, will be recycled

**Connection Pool Configuration Example:**

For production environments with higher traffic, you might configure:

```python
engine = create_engine(
    DATABASE_URL,
    pool_size=20,              # Keep 20 connections always ready
    max_overflow=40,           # Allow 40 more during spikes (total: 60)
    pool_timeout=30,           # Wait 30s for connection before error
    pool_recycle=3600,         # Recycle connections every hour
    pool_pre_ping=True,        # Test connection before using (catch stale connections)
    echo=False
)
```

The connection pool is invisible to your route handlers but provides massive performance benefits automatically!

### What are Database Migrations (Alembic)?

**The Problem**: Your database schema changes over time:
- Initially: Users have `email` and `username`
- Later: You add `created_at` timestamp
- Later: You add `is_active` boolean

How do you safely update production databases without losing data?

**Database Migrations** are version-controlled schema changes:
```
Initial state:           Migration 001:          Migration 002:
users table              Add created_at          Add is_active
- id                     - id                    - id
- email                  - email                 - email
- username               - username              - username
                         - created_at            - created_at
                                                 - is_active
```

<!-- ![alt text](archi_diagrams/Lab-2_alembic-migration.drawio.svg) -->
![Lab-2_alembic-migration](https://raw.githubusercontent.com/poridhiEng/lab-asset/main/FastAPI-Basics-Lab-assets/Lab-2/images/archi_diagrams/Lab-2_alembic-migration.drawio.svg)

**Alembic** is a migration tool for SQLAlchemy that:
- **Tracks** all schema changes in version files
- **Applies** migrations in order (upgrade)
- **Reverses** migrations if needed (downgrade)
- **Auto-generates** migration code from model changes
- **Works** across different environments (dev, staging, production)

Think of it like **Git for your database schema**.

### CRUD Operations

**CRUD** is an acronym for the four basic database operations:

| Operation | HTTP Method | SQL Command | Purpose |
|-----------|-------------|-------------|---------|
| **Create** | POST | INSERT | Add new records |
| **Read** | GET | SELECT | Retrieve records |
| **Update** | PUT/PATCH | UPDATE | Modify existing records |
| **Delete** | DELETE | DELETE | Remove records |

Every data-driven application implements these operations.

### Docker and Docker Compose

**Docker** packages applications in "containers" - isolated environments that run consistently everywhere.

**Docker Compose** defines multi-container applications in a simple YAML file.

**Why use Docker for PostgreSQL?**
-  No need to install PostgreSQL on your machine
-  Consistent setup across all developers
-  Easy to start/stop/reset the database
-  Isolated from other projects
-  Production-like environment locally

### Key Concepts

**Database Schema**: The structure of your database (tables, columns, types, constraints)

**Table**: A collection of related data (like a spreadsheet)

**Row/Record**: A single entry in a table (one user)

**Column/Field**: A specific attribute (email, username)

**Primary Key**: Unique identifier for each row (id)

**Foreign Key**: Links to another table (user_id in posts table)

**Index**: Speeds up queries on specific columns

**Constraint**: Rules enforced by the database (UNIQUE, NOT NULL)

**Session**: A workspace for database operations (like a transaction)

**Connection Pool**: Reuses database connections for efficiency

**Pydantic Schema**: Defines data structure for API requests/responses (validation)

## Project Structure

```
Lab-2/
├── docker-compose.yml      # PostgreSQL container configuration
├── .env                    # Environment variables (database URL, app name)
├── .env.example            # Template for environment variables
├── requirements.txt        # Python dependencies
├── alembic.ini             # Alembic configuration file
├── .gitignore              # Files to exclude from version control
│
├── app/                    # Main application package
│   ├── __init__.py         # Makes 'app' a Python package
│   ├── main.py             # FastAPI app + CRUD route handlers
│   ├── database.py         # Database engine, session, and Base class
│   ├── models.py           # SQLAlchemy models (database tables)
│   └── schemas.py          # Pydantic schemas (request/response validation)
│
└── alembic/                # Database migrations
    ├── env.py              # Alembic environment configuration
    ├── script.py.mako      # Template for new migrations
    ├── README              # Alembic documentation
    └── versions/           # Migration version files
        └── xxxx_create_users_table.py  # First migration (created by you)
```

**Architecture Components:**

1. **Client Layer**
   - Web browsers, API testing tools (cURL, Postman), and Python scripts
   - Send HTTP requests with JSON payloads

2. **FastAPI Application Layer**
   - **API Routes**: Define endpoints for CRUD operations
   - **Pydantic Schemas**: Validate incoming requests and serialize responses
   - **Business Logic**: Route handlers that orchestrate database operations
   - **Dependency Injection**: Manages database sessions lifecycle
   - **Auto-Documentation**: Automatically generated from code

3. **Database Layer**
   - **SQLAlchemy Engine**: Manages connection pool to PostgreSQL
   - **Sessions**: Handle database transactions and queries
   - **Models**: Python classes representing database tables
   - **Alembic**: Manages database schema migrations and versioning

4. **Data Storage Layer**
   - **Docker Compose**: Orchestrates PostgreSQL container
   - **PostgreSQL**: Stores persistent data in tables

5. **Configuration**
   - **.env**: Application and database connection settings
   - **docker-compose.yml**: Docker container configuration

**Request Flow Example (Creating a User):**
1. Client sends: `POST /users` with JSON `{"email": "ada@example.com", "username": "ada"}`
2. FastAPI receives request and validates JSON using Pydantic schema
3. FastAPI calls the `create_user` function with validated data
4. Function creates SQLAlchemy `User` object
5. SQLAlchemy translates to SQL: `INSERT INTO users ...`
6. PostgreSQL executes SQL and returns new user ID
7. SQLAlchemy creates Python `User` object with ID
8. FastAPI serializes object to JSON using Pydantic schema
9. Client receives: `{"id": 1, "email": "ada@example.com", "username": "ada"}`

## Step-by-Step Implementation Guide

### Step 1: Create Project Directory Structure

Create the following directory structure:

```bash
mkdir app
```

Your directory should look like:
```
code/
└── app/
```

### Step 2: Create `requirements.txt`

Create a file named `requirements.txt` with these dependencies:

```txt
fastapi==0.115.5
uvicorn[standard]==0.32.0
python-dotenv==1.0.1
SQLAlchemy==2.0.23
psycopg2-binary==2.9.10
pydantic==2.9.2
alembic==1.13.2
pydantic[email]
```

**What each package does:**
- **fastapi**: The web framework
- **uvicorn**: ASGI server to run FastAPI
- **python-dotenv**: Load environment variables from .env
- **SQLAlchemy**: ORM for database operations
- **psycopg2-binary**: PostgreSQL database adapter for Python
- **pydantic**: Data validation using Python type hints
- **alembic**: Database migration tool

### Step 3: Create `.env` File

Create `.env` file to store configuration:

```env
APP_NAME=FastAPI Lab 2
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/lab2_db
```

**Explanation:**
- `postgresql+psycopg2://` - Use PostgreSQL with psycopg2 driver
- `postgres:postgres` - username:password
- `@localhost:5432` - host and port
- `/lab2_db` - database name

### Step 4: Create `docker-compose.yml`

Create `docker-compose.yml` to run PostgreSQL in Docker:

```yaml
version: "3.9"

services:
  db:
    image: postgres:16
    container_name: lab2_postgres
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: lab2_db
    ports:
      - "5432:5432"
    volumes:
      - pgdata_lab2:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d lab2_db"]
      interval: 5s
      timeout: 5s
      retries: 20

volumes:
  pgdata_lab2:
```

### Step 5: Start PostgreSQL Container

```bash
# Start PostgreSQL in the background
docker compose up -d

# Check if container is running and healthy
docker compose ps

# View logs if needed
docker compose logs -f db
```

**Expected output:**
![alt text](images/image.png)

**Verify database is ready:**
```bash
docker compose exec db psql -U postgres -d lab2_db -c "SELECT version();"
```
![alt text](https://raw.githubusercontent.com/poridhiEng/lab-asset/main/FastAPI-Basics-Lab-assets/Lab-2/images/image-2.png)
<!-- ### Step 6: Install python3.12-venv
```
sudo apt install python3.12
```
On Debian/Ubuntu systems, you need to install the python3-venv
package using the following command in order to use the virtual environment.
![alt text](https://raw.githubusercontent.com/poridhiEng/lab-asset/main/FastAPI-Basics-Lab-assets/Lab-2/images/image-1.png) -->

### Step 6: Create Virtual Environment and Install Dependencies

```bash
# Create virtual environment
python -m venv .venv

# Activate it (Linux/Mac)
source .venv/bin/activate

# Install all dependencies
pip install -r requirements.txt
```

### Step 7: Create `app/__init__.py`

Create an empty file to make `app` a Python package:
```
touch app/__init__.py
```

### Step 8: Create `app/database.py`
```
touch app/database.py
```

This file sets up the database connection:

```python
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Load environment variables from .env file
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Base class for all models
class Base(DeclarativeBase):
    pass

# Create database engine
# echo=True would print all SQL queries (useful for debugging)
engine = create_engine(
    DATABASE_URL,
    echo=False,          # Set to True to see SQL queries
    future=True          # Use SQLAlchemy 2.0 style
)

# Create session factory
# Sessions are your "workspace" for database operations
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,     # Don't automatically flush changes
    autocommit=False,    # Don't automatically commit
    future=True          # Use SQLAlchemy 2.0 style
)
```

**Key Concepts:**
- **Engine**: Maintains a connection pool to the database
- **SessionLocal**: Factory that creates database sessions
- **Base**: All your models will inherit from this class
- **autocommit=False**: We manually control when to save changes
- **autoflush=False**: We manually control when to send changes to DB

### Step 9: Create `app/models.py`
```
touch app/models.py
```

Define the database table structure:

```python
from sqlalchemy import Column, Integer, String, UniqueConstraint
from .database import Base


class User(Base):
    __tablename__ = "users"

    # Primary key column
    id = Column(
        Integer,
        primary_key=True,  # Unique identifier
        index=True         # Create index for faster queries
    )

    # Email column
    email = Column(
        String(255),       # Maximum 255 characters
        nullable=False,    # Cannot be NULL
        unique=True,       # Must be unique across all users
        index=True         # Create index for faster lookups
    )

    # Username column
    username = Column(
        String(50),        # Maximum 50 characters
        nullable=False,    # Cannot be NULL
        unique=True,       # Must be unique across all users
        index=True         # Create index for faster lookups
    )

    # Table-level constraints
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        UniqueConstraint("username", name="uq_users_username"),
    )

    def __repr__(self):
        """String representation of User object."""
        return f"<User(id={self.id}, email='{self.email}', username='{self.username}')>"
```

**What this creates in PostgreSQL:**
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(50) NOT NULL UNIQUE
);

CREATE INDEX ix_users_id ON users (id);
CREATE INDEX ix_users_email ON users (email);
CREATE INDEX ix_users_username ON users (username);
```

### Step 10: Create `app/schemas.py`
```
touch app/schemas.py
```

Pydantic schemas for data validation:

```python
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr                          # Validates email format
    username: str = Field(
        min_length=3,                        # Minimum 3 characters
        max_length=50                        # Maximum 50 characters
    )


class UserUpdate(BaseModel):
    email: EmailStr | None = None            # Optional email
    username: str | None = Field(
        default=None,
        min_length=3,
        max_length=50
    )


class UserOut(BaseModel):
    id: int
    email: EmailStr
    username: str

    class Config:
        """Pydantic configuration."""
        from_attributes = True               # Allow creating from ORM models
```

**Why separate schemas?**
- **UserCreate**: Only accepts email + username (no ID)
- **UserUpdate**: All fields optional, for partial updates
- **UserOut**: Includes ID, used for responses (never for input)

**Benefits:**
- Automatic validation
- Clear API documentation
- Type safety
- Prevents sending unwanted data

### Step 11: Create `app/main.py`
```
touch app/main.py
```

The main FastAPI application with all CRUD endpoints:

```python
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .database import SessionLocal
from .models import User
from .schemas import UserCreate, UserUpdate, UserOut

# Load environment variables
load_dotenv()

# Create FastAPI application
app = FastAPI(
    title=os.getenv("APP_NAME", "FastAPI Lab 2"),
    description="A CRUD API for user management with PostgreSQL",
    version="1.0.0"
)


# Dependency: Database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Health check endpoint
@app.get("/ping")
def ping():
    return {"status": "ok", "message": "pong"}


# CREATE: Add a new user
@app.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    # Check if email or username already exists
    existing_user = db.query(User).filter(
        (User.email == payload.email) | (User.username == payload.username)
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email or username already exists"
        )

    # Create new user
    user = User(email=payload.email, username=payload.username)
    db.add(user)        # Add to session
    db.commit()         # Save to database
    db.refresh(user)    # Reload from database (get the ID)

    return user


# READ: Get all users
@app.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)):
    return db.query(User).order_by(User.id.asc()).all()


# READ: Get single user by ID
@app.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    return user


# UPDATE: Modify existing user
@app.put("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db)):
    # Get existing user
    user = db.get(User, user_id)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # Update email if provided and different
    if payload.email and payload.email != user.email:
        # Check if email already taken
        if db.query(User).filter(User.email == payload.email).first():
            raise HTTPException(
                status_code=400,
                detail="Email already in use"
            )
        user.email = payload.email

    # Update username if provided and different
    if payload.username and payload.username != user.username:
        # Check if username already taken
        if db.query(User).filter(User.username == payload.username).first():
            raise HTTPException(
                status_code=400,
                detail="Username already in use"
            )
        user.username = payload.username

    db.add(user)        # Mark as modified
    db.commit()         # Save changes
    db.refresh(user)    # Reload from database

    return user


# DELETE: Remove a user
@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    db.delete(user)     # Mark for deletion
    db.commit()         # Execute deletion

    return None         # 204 responses have no body
```

**Key Patterns:**
- **Dependency Injection**: `Depends(get_db)` automatically provides database session
- **Session Management**: Session is always closed, even if errors occur
- **Error Handling**: Raises `HTTPException` with appropriate status codes
- **Data Validation**: Pydantic automatically validates input/output
- **Database Operations**: Always `add()` → `commit()` → `refresh()`

### Step 12: Initialize Alembic

```bash
# Initialize Alembic in your project
alembic init alembic
```

This creates:
```
alembic/
├── env.py              # Environment configuration
├── README              # Alembic documentation
├── script.py.mako      # Template for new migrations
└── versions/           # Migration files go here

alembic.ini             # Alembic configuration file
```

### Step 13: Configure Alembic

**Edit `alembic/env.py`** to connect Alembic to your database and models:

Find this line (around line 21):
```python
target_metadata = None
```

Replace the entire section with:
```python
# Import your models
from app.database import Base
from app.models import User  # Import all models here

# Set target metadata from your models
target_metadata = Base.metadata
```

Also, find the `run_migrations_offline()` and `run_migrations_online()` functions and ensure they read from your `.env` file. Add this at the top of `env.py` after imports:

```python
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Override sqlalchemy.url with DATABASE_URL from .env
config.set_main_option('sqlalchemy.url', os.getenv('DATABASE_URL'))
```

**Edit `alembic.ini`** - Verify the `sqlalchemy.url` (line 63):
```ini
sqlalchemy.url = postgresql+psycopg2://postgres:postgres@localhost:5432/lab2_db
```

(This will be overridden by `.env`, but it's good to have a default)

### Step 14: Create and Apply Migration

```bash
# Generate migration from your models
alembic revision --autogenerate -m "Create users table"

# This creates a file like: alembic/versions/xxxx_create_users_table.py
```

**Review the generated migration file** in `alembic/versions/`:
![alt text](https://raw.githubusercontent.com/poridhiEng/lab-asset/main/FastAPI-Basics-Lab-assets/Lab-2/images/image-3.png)

**Apply the migration:**
```bash
# Apply all pending migrations
alembic upgrade head
```

**Expected output:**

![alt text](https://raw.githubusercontent.com/poridhiEng/lab-asset/main/FastAPI-Basics-Lab-assets/Lab-2/images/image-4.png)

**Verify the table was created:**
```bash
docker compose exec db psql -U postgres -d lab2_db -c "\dt"
docker compose exec db psql -U postgres -d lab2_db -c "\d users"
```
![alt text](https://raw.githubusercontent.com/poridhiEng/lab-asset/main/FastAPI-Basics-Lab-assets/Lab-2/images/image-5.png)

### Step 15: Run Your FastAPI Application

```bash
# Start the API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```


**Command breakdown:**
- `app.main`: Import `app` from `app/main.py`
- `app`: The FastAPI instance
- `--reload`: Auto-restart on code changes

**Expected output:**
![alt text](https://raw.githubusercontent.com/poridhiEng/lab-asset/main/FastAPI-Basics-Lab-assets/Lab-2/images/image.png)

### Step 16: Access FastAPI Application using Poridhi's Loadbalancer
To access the FastAPI Application with poridhi's Loadbalancer, use the following steps:

Find the wt0 IP address for the Poridhi's VM currently you are running by using the command:
```
ifconfig
```
![alt text](https://raw.githubusercontent.com/poridhiEng/lab-asset/main/FastAPI-Basics-Lab-assets/Lab-2/images/image-16.png)
Note: The wt0 IP in this image is wrong. It actually showed `100.125.246.186` IP when this lab was being done by the poridhi team, which is why on the next load balancer image, you see `100.125.246.186` IP. When you start a vm, you might get a different wt0 IP.

Go to Poridhi's LoadBalancer and Create a LoadBalancer with the wt0 IP and port 8000.
![alt text](https://raw.githubusercontent.com/poridhiEng/lab-asset/main/FastAPI-Basics-Lab-assets/Lab-2/images/image-15.png)

### Step 17: Test Your API

#### Open Interactive Documentation

**Swagger UI**: <|Load Balancer URL|>/docs

![alt text](https://raw.githubusercontent.com/poridhiEng/lab-asset/main/FastAPI-Basics-Lab-assets/Lab-2/images/image-14.png)

This is your best friend! You can:
- See all endpoints
- Try requests directly in the browser
- View request/response schemas
- See validation rules

## How It Works (Code Basics)
- `database.py` creates an engine with `DATABASE_URL` and a `SessionLocal` for requests.
- `models.py` maps the `User` class to the `users` table with uniqueness on `email` and `username`.
- `schemas.py` defines `UserCreate`, `UserUpdate`, and `UserOut` for input/output validation.
- `main.py` wires routes to DB operations using a session dependency (`get_db`).
- `alembic/env.py` loads `DATABASE_URL` and migrates based on `Base.metadata`.

#### Method 1: Using Swagger UI (Recommended for Beginners)

1. Open <|Load Balancer URL|>/docs
2. Find the `POST /users` endpoint
3. Click "Try it out"
4. Enter JSON:
   ```json
   {
     "email": "alice@example.com",
     "username": "alice"
   }
   ```
5. Click "Execute"
6. See response with status 201 and the created user with ID

Try all endpoints this way - it's interactive and visual!

#### Method 2: Using CURL (Command Line)

```bash
# CREATE: Add a new user
curl -X POST "<|Load Balancer URL|>/users" \
  -H "Content-Type: application/json" \
  -d '{"email": "bob@example.com", "username": "bob"}'
```
![alt text](https://raw.githubusercontent.com/poridhiEng/lab-asset/main/FastAPI-Basics-Lab-assets/Lab-2/images/image-13.png)
```bash
# READ: Get all users
curl -X GET "<|Load Balancer URL|>/users"
```
![alt text](https://raw.githubusercontent.com/poridhiEng/lab-asset/main/FastAPI-Basics-Lab-assets/Lab-2/images/image-12.png)
```bash
# READ: Get specific user
curl -X GET "<|Load Balancer URL|>/users/1"
```
![alt text](https://raw.githubusercontent.com/poridhiEng/lab-asset/main/FastAPI-Basics-Lab-assets/Lab-2/images/image-11.png)
```bash
# UPDATE: Modify user
curl -X PUT "<|Load Balancer URL|>/users/1" \
  -H "Content-Type: application/json" \
  -d '{"email": "bob.smith@example.com"}'
```
![alt text](https://raw.githubusercontent.com/poridhiEng/lab-asset/main/FastAPI-Basics-Lab-assets/Lab-2/images/image-9.png)
```bash
# DELETE: Remove user
curl -X DELETE "<|Load Balancer URL|>/users/1"
```
![alt text](https://raw.githubusercontent.com/poridhiEng/lab-asset/main/FastAPI-Basics-Lab-assets/Lab-2/images/image-7.png)


#### Method 3: Using Python Requests

Create `test_users.py`:

```python
import requests

BASE_URL = "http://127.0.0.1:8000"

# CREATE a user
response = requests.post(
    f"{BASE_URL}/users",
    json={"email": "charlie@example.com", "username": "charlie"}
)
print(f"CREATE: {response.status_code}")
print(response.json())
user_id = response.json()["id"]

# READ all users
response = requests.get(f"{BASE_URL}/users")
print(f"\nREAD ALL: {response.status_code}")
print(response.json())

# READ single user
response = requests.get(f"{BASE_URL}/users/{user_id}")
print(f"\nREAD ONE: {response.status_code}")
print(response.json())

# UPDATE user
response = requests.put(
    f"{BASE_URL}/users/{user_id}",
    json={"email": "charlie.new@example.com"}
)
print(f"\nUPDATE: {response.status_code}")
print(response.json())

# DELETE user
response = requests.delete(f"{BASE_URL}/users/{user_id}")
print(f"\nDELETE: {response.status_code}")
```

Run it:
```bash
pip install requests
python test_users.py
```

### Verify Data in Database

You can directly query the PostgreSQL database:

```bash
# Connect to database
docker compose exec db psql -U postgres -d lab2_db

# List all users
SELECT * FROM users;

# Count users
SELECT COUNT(*) FROM users;

# Exit psql
\q
```

### Step 18: Modify Schema with Another Migration

Now let's demonstrate a real-world scenario: adding new columns to an existing table. This shows how Alembic helps you evolve your database schema over time.

**Why Another Migration?**
In production, you'll often need to:
- Add new features (new columns)
- Change existing columns
- Add indexes for performance
- Maintain backward compatibility

Let's add `created_at` and `is_active` columns to track when users were created and whether they're active.

#### 18.1: Update the User Model

Edit `app/models.py`:

```python
from sqlalchemy import Column, Integer, String, UniqueConstraint, DateTime, Boolean
from sqlalchemy.sql import func
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)

    # New columns
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
```

**What changed:**
- Added `DateTime` and `Boolean` imports
- Added `func` from `sqlalchemy.sql` for `func.now()`
- `created_at`: Automatically set to current timestamp when row is created
- `is_active`: Defaults to `True`, allows soft-deletion (marking users inactive instead of deleting)

#### 18.2: Generate Migration

```bash
alembic revision --autogenerate -m "Add created_at and is_active to users"
```

**Expected output:**

<!-- ![alt text](image-100.png) -->
![image-100](https://raw.githubusercontent.com/poridhiEng/lab-asset/main/FastAPI-Basics-Lab-assets/Lab-2/images/image-100.png)

#### 18.3: Review Generated Migration

Open the newly created file in `alembic/versions/` (e.g., `abc123_add_created_at_and_is_active_to_users.py`):

<!-- ![alt text](image-101.png) -->
![image-101](https://raw.githubusercontent.com/poridhiEng/lab-asset/main/FastAPI-Basics-Lab-assets/Lab-2/images/image-101.png)

**Understanding the migration:**
- `upgrade()`: Adds the new columns
- `downgrade()`: Removes them (allows rolling back)
- `server_default`: Sets default values for existing rows
- Alembic detected changes automatically!

#### 18.4: Apply the Migration

```bash
alembic upgrade head
```

**Expected output:**

<!-- ![alt text](image-102.png) -->
![image-102](https://raw.githubusercontent.com/poridhiEng/lab-asset/main/FastAPI-Basics-Lab-assets/Lab-2/images/image-102.png)

#### 18.5: Verify New Columns in Database

```bash
# Check table structure
docker compose exec db psql -U postgres -d lab2_db -c "\d users"
```

**Expected output:**

<!-- ![alt text](image-105.png) -->
![image-105](https://raw.githubusercontent.com/poridhiEng/lab-asset/main/FastAPI-Basics-Lab-assets/Lab-2/images/image-105.png)

**Verify existing data got default values:**
```bash
docker compose exec db psql -U postgres -d lab2_db -c "SELECT id, username, created_at, is_active FROM users;"
```

You should see existing users now have `created_at` set to migration time and `is_active = true`.

<!-- ![alt text](image-106.png) -->
![image-106](https://raw.githubusercontent.com/poridhiEng/lab-asset/main/FastAPI-Basics-Lab-assets/Lab-2/images/image-106.png)

**What You've Learned:**

This second migration demonstrates the real power of Alembic. In production applications, your database schema constantly evolves:
- New features require new columns
- Performance optimization needs new indexes
- Business requirements change over time

With Alembic, you can:
- **Modify your models** in Python (add columns, change types, etc.)
- **Generate migrations** automatically with `alembic revision --autogenerate`
- **Apply changes** safely to any environment with `alembic upgrade head`
- **Rollback if needed** using `alembic downgrade -1`
- **Track all changes** in version control alongside your code

**Real-World Impact:**
Imagine you have 10,000 users in production and need to add a `last_login` column. With Alembic:
1. Modify model locally
2. Generate migration
3. Test on staging database
4. Apply to production: `alembic upgrade head`
5. All 10,000 users get the new column with default values
6. Zero downtime, zero data loss!

Without migrations, you'd manually write SQL, risk inconsistencies between environments, and potentially lose data.

**Key Takeaway:**
Alembic migrations are version control for your database schema. Just like Git tracks code changes, Alembic tracks schema changes, enabling safe evolution across development, staging, and production environments.



## Conclusion

Congratulations on completing Lab 2! You've built a production-ready CRUD API with FastAPI and PostgreSQL, learned how SQLAlchemy manages database connections efficiently through connection pooling, and mastered Alembic migrations for evolving your database schema safely. These fundamentals form the backbone of modern web applications—from handling thousands of concurrent users to deploying schema changes in production without downtime. You're now equipped to build robust, scalable APIs that connect to real databases. 