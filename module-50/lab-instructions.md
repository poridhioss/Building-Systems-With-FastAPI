This module groups the work into three distinct labs: **The Foundation (User Management)**, **The Core (Authentication Logic)**, and **The Lifecycle (Session Management)**.

---

### **Lab 1: User Management & Security Foundation**
**Context:** In this lab, students set up the project infrastructure and handle the "static" side of authentication: storing users securely. This combines database design with the registration flow.

*   **Goals:**
    *   Initialize the FastAPI environment and configure the database connection (SQLAlchemy/SQLModel).
    *   **Design the SQL Schema:** Create the User table model (ID, Email, `is_active`, `hashed_password`).
    *   **Security Implementation:** Implement `bcrypt` to handle password hashing (never store plain text!).
    *   **Registration:** Build the `POST /register` endpoint to validate input and save the new user to the database.
*   **Deliverables:**
    *   A Python file defining the User DB model.
    *   A utility function `get_password_hash(password)`.
    *   A functional `POST /register` endpoint.
    *   **Validation:** A database check confirming that new users are saved with hashed passwords (e.g., `$2b$12$...`).

---

### **Lab 2: The Authentication Core (Login & Protection)**
**Context:** This lab covers the "dynamic" side of authentication. Students will build the mechanism to issue tokens (Login) and the middleware to verify them (Protection), covering the bulk of the JWT theory.

*   **Goals:**
    *   **Credential Verification:** Create a function to verify incoming passwords against the stored hashes.
    *   **JWT Creation:** Implement the logic to encode the JWT Header, Payload (Subject), and Signature using `HS256`.
    *   **Login Endpoint:** Build `POST /login` that returns an access token.
    *   **Middleware/Dependency:** Understand the FastAPI request lifecycle by building the `get_current_user` dependency. This must decode the token, validate the signature, and fetch the user.
    *   **Protected Routes:** specific endpoints (e.g., `GET /users/me`) using the new dependency.
*   **Deliverables:**
    *   A utility function `verify_password(plain, hashed)`.
    *   A utility function `create_access_token(data)`.
    *   A working `POST /login` route returning a JWT.
    *   A protected `GET /users/me` route that returns user profile data only when a valid token is provided in the header.

---

### **Lab 3: Lifecycle Management (Expiration & Refresh)**
**Context:** The final lab turns a basic script into a production-ready API. It focuses on the specific objective of "Handling token expiration and implementing refresh token strategies."

*   **Goals:**
    *   **Expiration Logic:** Modify the token generation to enforce strict expiration times (e.g., 15 mins for Access, 7 days for Refresh).
    *   **Dual-Token Architecture:** Refactor the login endpoint to issue *two* tokens (Access & Refresh).
    *   **Refresh Endpoint:** Create a `POST /refresh` endpoint. This endpoint validates a long-lived Refresh Token and issues a new short-lived Access Token without requiring the user's password.
    *   **Error Handling:** Ensure the API throws specific `401 Unauthorized` errors when tokens are expired.
*   **Deliverables:**
    *   Refactored `POST /login` response schema (includes `refresh_token`).
    *   A functional `POST /refresh` endpoint.
    *   **Scenario Test:** A demonstration where the student manually sets a token to expire in 1 second, waits for it to expire, attempts to access a protected route (fails), and then successfully uses the refresh endpoint to regain access.