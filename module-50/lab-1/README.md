# Lab 1 – User Management & Security Foundation

Welcome to Lab 1 of the Authentication & Authorization series! In this lab, you'll build the foundation of a secure authentication system by implementing user registration with proper password security. You'll learn how to safely store user credentials using industry-standard password hashing, set up a PostgreSQL database with Docker, and create a registration API endpoint.

![alt text](images/archi-diagrams/mod50-lab-1_high-level.drawio.svg)

## Objectives

- Set up FastAPI project with PostgreSQL database
- Design and implement User database schema
- Understand password security fundamentals
- Implement bcrypt password hashing
- Build secure user registration endpoint (POST /register)
- Validate user input with Pydantic schemas
- Test registration with multiple methods
- Verify secure password storage in database

## Background

### Why Do We Need Secure Authentication?

Authentication is the process of verifying the identity of a user. Every modern application needs to identify who is accessing the system, protect resources so that only authorized users can access specific data, maintain user trust by handling their credentials responsibly, and comply with regulations like GDPR and CCPA that require proper data protection.

The golden rule of password security is simple: **NEVER store passwords in plain text!** If anyone with database access can read passwords directly, you're putting every user at risk. Imagine if a hacker breaches your database and finds this:

### What is Password Hashing?

Hashing is a one-way cryptographic function that transforms a password into a fixed-length string of characters. Think of it like putting your password through a meat grinder - you can turn meat into ground beef, but you can't reassemble the original steak from the ground beef. The process is intentionally irreversible.

Hashing has some important properties. First, it's one-way, meaning you cannot reverse the hash to get the original password. Second, it's deterministic, so the same password always produces the same hash. Third, different passwords produce different hashes, and fourth, the output is always the same length regardless of how long or short your input password is.

**How it works:**
```
User enters: "mySecurePass123"
        ↓
    Hash Function (bcrypt)
        ↓
Output: "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyE..."
```

You might wonder why we can't just reverse it. Well, hashing uses complex mathematical operations with multiple rounds of encryption, and information is intentionally lost during the process. Even if you have the hash, you simply cannot compute the original password from it. It's mathematically infeasible.

When a user tries to log in later, we don't decrypt their stored password (because we can't). Instead, we take their login attempt, hash it the same way, and compare the two hashes. If they match, the password is correct.

**Verification Process:**
```
Login attempt: User enters "mySecurePass123"
        ↓
Hash the input: bcrypt.hash("mySecurePass123")
        ↓
Compare: Does new hash match stored hash?
        ↓
    Yes → Allow login
    No  → Deny login
```

### What is bcrypt?

bcrypt is a password hashing function designed specifically for securely storing passwords. It was designed in 1999 and remains one of the best choices today, which tells you something about how well it was architected.

What makes bcrypt special? Unlike regular hash functions that are designed to be fast, bcrypt is intentionally slow. It takes about 100-300 milliseconds to hash a password, which might seem like a bug, but it's actually the main feature. This slowness makes brute-force attacks impractical - if an attacker tries to guess millions of passwords, each guess takes a fraction of a second, turning a days-long attack into a decades-long attack.

bcrypt also automatically salts your passwords. A salt is random data added to the password before hashing, which ensures that even if two users have the same password, they'll have different hashes. This prevents rainbow table attacks, where attackers use precomputed tables of common password hashes.

**bcrypt anatomy:**
```
$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyE...
│  │  │  │                                    │
│  │  │  └─ Salt (random data)                └─ Hash
│  │  └─ Work factor (2^12 = 4096 rounds)
│  └─ bcrypt version
└─ Algorithm identifier
```

The work factor (also called cost factor) determines how many iterations the algorithm runs. The default is 12, which means 4,096 iterations. A higher work factor makes hashing slower and more secure. Each increment doubles the computation time, so work factor 13 would take twice as long as 12. For web applications, 12-14 is recommended as it balances security with acceptable response times.

The salt is random data added to your password before hashing. This ensures that the same password produces different hashes for different users, preventing rainbow table attacks where attackers maintain precomputed databases of common passwords and their hashes. bcrypt handles salting automatically, so you don't need to worry about generating or storing salts yourself.

You might have heard of alternatives like Argon2 (the winner of the 2015 Password Hashing Competition), scrypt (a memory-hard function), or PBKDF2 (an older but still acceptable standard). Never use MD5 or SHA1 for passwords though - they're too fast and don't include salting, making them vulnerable to modern attacks.

For this lab, we're using bcrypt because it's well-supported in Python through the `passlib` library, proven secure over 20+ years of real-world use, easy to implement correctly, and the default choice for most web frameworks. If you're starting a new project today, bcrypt is still an excellent choice.

### Database Schema Design

Our User table will store the essential information needed for authentication:

```
users table:
┌──────────────┬─────────────────┬──────────────┬─────────────────────────────┐
│ Column       │ Type            │ Constraints  │ Purpose                     │
├──────────────┼─────────────────┼──────────────┼─────────────────────────────┤
│ id           │ INTEGER         │ PRIMARY KEY  │ Unique identifier           │
│ email        │ VARCHAR(255)    │ UNIQUE       │ User's email (for login)    │
│ is_active    │ BOOLEAN         │ DEFAULT TRUE │ Account status              │
│ hashed_pass  │ VARCHAR(255)    │ NOT NULL     │ Hashed password (bcrypt)    │
└──────────────┴─────────────────┴──────────────┴─────────────────────────────┘
```

The `id` field is an auto-incrementing integer that serves as our primary key for database efficiency. We use `email` as the username for login since it's already unique and familiar to users. The `is_active` boolean field allows us to do soft-deletes, meaning we can disable an account without actually removing the data from our database. Finally, `hashed_password` stores the bcrypt hash - notice it's NOT called "password" because we never store the plain password.

### Key Concepts

Before we dive into implementation, let's clarify the difference between authentication and authorization. Authentication asks "Who are you?" - it's about proving your identity. Authorization asks "What can you do?" - it's about permissions and access control. In this lab, we're focused on authentication, but these concepts work hand-in-hand in real applications.

When it comes to password security, there are some fundamental principles you should always follow. Never store plain text passwords under any circumstances. Always use strong hashing algorithms like bcrypt or Argon2. Make sure every password is salted to prevent rainbow tables. Choose appropriate work factors that balance security with performance - too low and you're vulnerable, too high and your users will wait forever to log in. Never log passwords, even hashed ones, because logs often end up in less secure places than your database. And finally, validate password strength during registration to encourage users to choose secure passwords.

You'll also need to understand HTTP status codes for proper API responses. When a user successfully registers, return `201 Created` to indicate a new resource was created. If they provide invalid input like a malformed email or too-short password, return `400 Bad Request` or `422 Unprocessable Entity`. If they try to register with an email that already exists, return `409 Conflict` to indicate the resource conflicts with existing data.

Pydantic validation is what makes all this input checking easy. It validates email format automatically using `EmailStr`, enforces password minimum length requirements, provides automatic OpenAPI documentation so your API docs are always up-to-date, and returns clear error messages to clients when validation fails.

## Project Structure

```
Root directory
    ├── docker-compose.yml      # PostgreSQL container configuration
    ├── .env                    # Environment variables (DATABASE_URL)
    ├── .env.example            # Template for environment variables
    ├── requirements.txt        # Python dependencies
    ├── alembic.ini             # Alembic configuration
    ├── .gitignore              # Git ignore patterns
    │
    ├── app/                    # Main application package
    │   ├── __init__.py         # Package marker
    │   ├── main.py             # FastAPI app + registration endpoint
    │   ├── database.py         # Database engine, session, Base
    │   ├── models.py           # SQLAlchemy User model
    │   ├── schemas.py          # Pydantic schemas (UserCreate, UserOut)
    │   └── utils.py            # Password hashing utilities
    │
    └── alembic/                # Database migrations
        ├── env.py              # Alembic environment
        ├── script.py.mako      # Migration template
        └── versions/           # Migration files
            └── xxxx_create_users_table.py
```

The architecture follows a layered approach. At the top, we have the client layer where HTTP clients like browsers, Postman, or curl send registration requests with email and password, then receive confirmation with a user ID. The API layer built with FastAPI handles route handlers for POST /register, validates input using Pydantic schemas for email format and password length, contains business logic to check for duplicate emails and hash passwords, and manages error handling for cases like duplicate emails or invalid input.

The security layer sits between the API and database, handling password hashing with bcrypt, performing input validation and sanitization, and managing security headers and CORS policies. Below that, the database layer uses SQLAlchemy ORM models, manages connection pooling for efficiency, handles transaction management to ensure data consistency, and uses Alembic for database migrations. Finally, the data storage layer consists of a PostgreSQL database running in a Docker container with a persistent volume to ensure data survives container restarts.

When a user registers, here's what happens: The client sends a POST request to /register with a JSON body containing email and password. FastAPI receives this and validates the input using the Pydantic schema, checking if the email format is valid and if the password is at least 8 characters. We then check if the email already exists in the database with a SELECT query. If it's new, we hash the password using bcrypt, transforming something like "SecurePass123!" into "$2b$12$LQv3c1yqBWVH...". We create a User object and save it to the database with an INSERT statement. Finally, we return a success response with the new user's ID, email, and active status - notably, without the password.

## Step-by-Step Implementation Guide

### Step 1: Create Project Directory Structure

```bash
mkdir app
```

Your directory should look like:
```
app/
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
passlib[bcrypt]==1.7.4
bcrypt==4.0.1
```

FastAPI is our web framework for building APIs. Uvicorn is the ASGI server that actually runs FastAPI applications. Python-dotenv loads environment variables from our .env file so we don't hardcode sensitive information. SQLAlchemy is the ORM that lets us work with databases using Python objects instead of raw SQL. Psycopg2-binary is the PostgreSQL adapter that SQLAlchemy uses under the hood. Pydantic provides data validation using Python type hints. Alembic is our database migration tool that tracks schema changes. The pydantic[email] extra adds email validation support, and passlib[bcrypt] is our password hashing library with bcrypt support.

### Step 3: Create `.env` File

Create `.env` file to store configuration:

```env
APP_NAME=FastAPI Auth Lab 1
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/auth_lab1_db
```

The APP_NAME is just a friendly name shown in your API documentation. The DATABASE_URL is more important - it's the connection string that tells SQLAlchemy how to connect to PostgreSQL. It starts with `postgresql+psycopg2://` to specify we're using PostgreSQL with the psycopg2 driver. Then comes `postgres:postgres`, which is username:password (in production, you'd use stronger credentials). The `@localhost:5432` part specifies the host and port, and `/auth_lab1_db` is the database name.

### Step 4: Create `.env.example`

Create `.env.example` as a template (for version control):

```env
APP_NAME=FastAPI Auth Lab 1
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/auth_lab1_db
```

### Step 5: Create `.gitignore`

Create `.gitignore` to exclude sensitive files:

```
# Virtual environment
.venv/
venv/
env/

# Environment variables
.env

# Python cache
__pycache__/
*.pyc
*.pyo
*.pyd

# Database
*.db
*.sqlite3

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db

# Alembic
alembic/versions/*.pyc
```

### Step 6: Create `docker-compose.yml`

Create `docker-compose.yml` to run PostgreSQL:

```yaml
version: "3.9"

services:
  db:
    image: postgres:16
    container_name: auth_lab1_postgres
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: auth_lab1_db
    ports:
      - "5432:5432"
    volumes:
      - pgdata_auth_lab1:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d auth_lab1_db"]
      interval: 5s
      timeout: 5s
      retries: 20

volumes:
  pgdata_auth_lab1:
```

This Docker Compose configuration sets up PostgreSQL 16 in a container. The container name makes it easy to identify when running docker commands. The environment variables set up the database credentials to match our .env file. The ports section exposes PostgreSQL on port 5432 so our FastAPI app can connect to it. The volumes section ensures data persists across container restarts - without this, stopping the container would delete all your data. The healthcheck verifies the database is ready before we try to connect to it.

### Step 7: Start PostgreSQL Container

```bash
# Start PostgreSQL in the background
docker compose up -d

# Check if container is running and healthy
docker compose ps

# View logs if needed
docker compose logs -f db
```

**Expected output:**
![alt text](./images/image.png)

**Verify database is ready:**
```bash
docker compose exec db psql -U postgres -d auth_lab1_db -c "SELECT version();"
```

You should see PostgreSQL version information.

### Step 8: Create Virtual Environment and Install Dependencies

```bash
# Create virtual environment
python -m venv .venv

# Activate it
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install all dependencies
pip install -r requirements.txt
```
### Step 9: Create `app/__init__.py`

Create an empty file to make `app` a Python package:

```bash
touch app/__init__.py
```

Or create an empty file with your editor.

### Step 10: Create `app/database.py`

Create `app/database.py` for database configuration:

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
# echo=False: Don't print SQL queries (set True for debugging)
# future=True: Use SQLAlchemy 2.0 style
engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True
)

# Create session factory
# Sessions are your "workspace" for database operations
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,     # Don't automatically flush changes
    autocommit=False,    # Don't automatically commit (we control transactions)
    future=True
)
```

The engine is what maintains the connection pool to your database. Think of it as the manager that handles all the low-level database connections. SessionLocal is a factory that creates database sessions - each request will get its own session. The Base class is what all your models will inherit from, giving them ORM functionality. We set autocommit to False because we want explicit control over when changes are saved to the database, which is safer and more predictable.

### Step 11: Create `app/models.py`

Create `app/models.py` to define the User model:

```python
from sqlalchemy import Column, Integer, String, Boolean
from .database import Base


class User(Base):
    __tablename__ = "users"

    # Primary key
    id = Column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True
    )

    # Email (used as username for login)
    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )

    # Hashed password (NEVER store plain text!)
    hashed_password = Column(
        String(255),
        nullable=False
    )

    # Account status (allows soft-delete)
    is_active = Column(
        Boolean,
        default=True,
        nullable=False
    )

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', is_active={self.is_active})>"
```

The `id` column is our auto-incrementing primary key. We make it indexed because we'll frequently look up users by ID. The `email` column is set to unique because each user needs a distinct email, and we index it since we'll be searching by email during login. Notice the `hashed_password` column - the name reminds us that we NEVER store plain text passwords here. The `is_active` boolean allows us to soft-delete accounts by setting them to inactive instead of removing the data entirely.

**What this creates in PostgreSQL:**
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX ix_users_id ON users (id);
CREATE INDEX ix_users_email ON users (email);
```

### Step 12: Create `app/schemas.py`

Create `app/schemas.py` for Pydantic validation schemas:

```python
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)


class UserOut(BaseModel):
    id: int
    email: EmailStr
    is_active: bool

    class Config:
        from_attributes = True  # Allow creating from ORM models
```

We use separate schemas for input and output for good reason. UserCreate accepts email and password from the user during registration. The password is validated for minimum length but is NEVER stored as-is or returned in any response. UserOut is what we send back to the client - it includes the id, email, and is_active status, but deliberately excludes any password information. This separation ensures we never accidentally expose sensitive data.

Notice that UserOut has a Config class with `from_attributes = True`. This tells Pydantic it can create these schema objects from ORM models, which is how we convert our database User objects into JSON responses.

### Step 13: Create `app/utils.py`

Create `app/utils.py` for password hashing utilities:

```python
from passlib.context import CryptContext

# Create password context with bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    # Hash a plain text password using bcrypt
    return pwd_context.hash(password)
```

The `pwd_context` configures passlib to use bcrypt with automatic deprecation handling in case we want to upgrade to a stronger algorithm later. The `get_password_hash()` function takes a plain text password and returns a bcrypt hash starting with "$2b$12$..." - you'll use this during registration. 

When you call `get_password_hash("myPassword")`, bcrypt generates a random salt, combines the password with the salt, applies 4096 rounds of the bcrypt algorithm (because work factor is 12), and returns the result as "$2b$12$<salt><hash>".

### Step 14: Create `app/main.py`

Create `app/main.py` with the FastAPI application:

```python
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from .database import SessionLocal
from .models import User
from .schemas import UserCreate, UserOut
from .utils import get_password_hash

# Load environment variables
load_dotenv()

# Create FastAPI application
app = FastAPI(
    title=os.getenv("APP_NAME", "FastAPI Auth Lab 1"),
    description="User registration with secure password hashing",
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


# User registration endpoint
@app.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserCreate, db: Session = Depends(get_db)):
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == payload.email).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    # Hash the password (NEVER store plain text!)
    hashed_password = get_password_hash(payload.password)

    # Create new user instance
    new_user = User(
        email=payload.email,
        hashed_password=hashed_password,
        is_active=True
    )

    try:
        # Add to session and commit to database
        db.add(new_user)
        db.commit()
        db.refresh(new_user)  # Reload from DB to get the ID

        return new_user

    except IntegrityError:
        # Rollback in case of database constraint violation
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
```

Let's walk through what this code does. The health check endpoint at `/ping` is simple - it just returns a status message so you can verify the API is running. The `get_db()` function is a dependency that creates a database session for each request and automatically closes it when the request finishes, even if an error occurs.

The registration endpoint at `POST /register` is where the real work happens. First, we check if the email already exists in the database. If it does, we return a 409 Conflict error. Next, we hash the password using bcrypt - this is critical for security, we NEVER store the plain text password. Then we create a new User instance with the email, hashed password, and is_active set to True. We add it to the session, commit to save it to the database, and refresh to get the auto-generated ID. Finally, we return the new user object, which Pydantic automatically converts to the UserOut schema, ensuring the password isn't included in the response.

The try-except block catches IntegrityError, which happens if there's a database constraint violation like a duplicate email sneaking through our earlier check due to race conditions. We rollback the transaction and return an appropriate error message.

### Step 15: Initialize Alembic

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

### Step 16: Configure Alembic

**Edit `alembic/env.py`** to connect Alembic to your models.

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

Also, add this at the top of `env.py` after imports (around line 8 after `config = context.config`):
```python
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Override sqlalchemy.url with DATABASE_URL from .env
config.set_main_option('sqlalchemy.url', os.getenv('DATABASE_URL'))
```

**Edit `alembic.ini`** - Verify the `sqlalchemy.url` (around line 63):
```ini
sqlalchemy.url = postgresql+psycopg2://postgres:postgres@localhost:5432/auth_lab1_db
```

This will be overridden by `.env`, but it's good to have a default.

### Step 17: Create and Apply Migration

```bash
# Generate migration from your models
alembic revision --autogenerate -m "Create users table"
```

This creates a file like: `alembic/versions/xxxx_create_users_table.py`

**Apply the migration:**
```bash
alembic upgrade head
```

**Expected output:**
```
INFO  [alembic.runtime.migration] Running upgrade  -> xxxx, Create users table
```

**Verify table was created:**
```bash
# List all tables
docker compose exec db psql -U postgres -d auth_lab1_db -c "\dt"

# Describe users table structure
docker compose exec db psql -U postgres -d auth_lab1_db -c "\d users"
```

### Step 18: Run Your FastAPI Application

```bash
# Start the API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The `app.main:app` tells Uvicorn to import the `app` object from `app/main.py`. The `--reload` flag makes the server auto-restart when you change code, which is great for development but shouldn't be used in production. The `--host 0.0.0.0` makes it listen on all network interfaces, and `--port 8000` runs it on port 8000.

**Expected output:**

![alt text](./images/image-1.png)

### Step 19: Access FastAPI Application using Poridhi's Load Balancer

![alt text](./images/image-2.png)

![alt text](./images/image-3.png)

To access the FastAPI application with Poridhi's Load Balancer, first find your wt0 IP address by running `ifconfig` and looking for the `wt0` interface. Note the IP address (something like `100.125.246.186`). Then go to Poridhi's Load Balancer dashboard, create a new Load Balancer, use your wt0 IP address with port 8000, and click "Create". You'll receive a public URL like `https://lb-xxxxx.poridhi.io` that you can use to access your API from anywhere.

### Step 20: Test Your API

#### Method 1: Using Swagger UI (Recommended)

![alt text](./images/image-4.png)

Open your browser and go to `<Load Balancer URL>/docs` to see the interactive API documentation. Click on `POST /register` to expand it, then click "Try it out". Enter test data like:

```json
{
  "email": "alice@example.com",
  "password": "SecurePass123!"
}
```

Click "Execute" and check the response. You should see status code 201 Created and a response like:

![alt text](./images/image-5.png)

Try registering another valid user with `bob@example.com` and a different password - this should work. Now try registering with an invalid email like "notanemail" - you should get 422 Unprocessable Entity. Try a password that's too short like "short" - again, 422. Finally, try registering Alice again with the same email - you should get 409 Conflict with the message "Email already registered".

#### Method 2: Using curl (Command Line in your local pc or poridhi vm)

```bash
# Register a new user
curl -X POST "<Load Balancer URL>/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "david@example.com",
    "password": "SecurePassword123"
  }'
```

**Expected response:**

![alt text](./images/image-6.png)

### Step 21: Verify Password Hashing in Database

This is the most important verification step - making sure passwords are actually being hashed securely. Query the database:

```bash
docker compose exec db psql -U postgres -d auth_lab1_db -c "SELECT id, email, hashed_password, is_active FROM users;"
```

**Expected output:**

![alt text](./images/image-7.png)

Look at those hashed_password values. Each one starts with "$2b$12$", which tells you it's a bcrypt hash with work factor 12. Notice that even if two users had chosen the same password, their hashes would be completely different because bcrypt adds a unique salt to each one. You cannot reverse these hashes to get the original passwords - it's mathematically infeasible. And all the hashes are roughly the same length (around 60 characters), regardless of how long the original password was.

## Conclusion

Congratulations! You've built a secure user registration system with proper password hashing. You now understand why password security matters and why you should never store plain text passwords. You've learned how bcrypt works with its slow hashing, automatic salting, and configurable work factors. You've designed a database schema with proper separation between user credentials and sensitive data. You've implemented FastAPI route handlers with dependency injection and Pydantic validation. You've used SQLAlchemy ORM models and database sessions. And you've worked with Alembic for database migrations that version-control your schema changes.

This foundation is critical for building secure authentication systems. The principles you've learned about hashing, validation, and error handling apply to all modern web applications. Security starts at the foundation - by properly hashing passwords from day one, you protect your users even if your database is compromised. Even if an attacker gains access to your database, all they'll see are irreversible hashes.
