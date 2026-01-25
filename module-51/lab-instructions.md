### Proposed Lab Structure (3 Labs)

Since there are three distinct deployment strategies listed in the objectives, it makes the most sense to break this into **3 Labs**, with one lab dedicated to each architecture.

#### **Lab 1: Containerization & Cloud Basics (Poridhi Cloud)**
**Context:** Before tackling complex AWS configurations, students need to learn how to package their application so it runs anywhere. This lab focuses on Dockerizing the application and doing a "Lift and Shift" deployment to Poridhi Cloud.

*   **Goals:**
    *   **Containerization:** Write a `Dockerfile` to package the FastAPI app and its dependencies (requirements.txt).
    *   **Build & Push:** Build the Docker image and push it to the container registry.
    *   **Deployment:** Deploy the containerized app onto the Poridhi Cloud platform.
    *   **Environment Config:** Configure basic environment variables (like the `SECRET_KEY`) in the cloud console.
*   **Deliverables:**
    *   A valid `Dockerfile`.
    *   A live, public URL (This is basically the poridhi load balancer URL) where the `/health` endpoint returns `200 OK`.

### **Lab 2: Containerized Deployment on AWS EC2**
**Context:** This is the "Infrastructure as a Service" (IaaS) lab. Unlike Lab 1 where the platform managed the container, here students will manage the server themselves. They will verify that the exact same Docker setup from Lab 1 works on a live AWS server by manually installing the Docker runtime and deploying the stack.

*   **Goals:**
    *   **Environment Setup:** Connect to an existing **AWS EC2** instance (Ubuntu) and install the Docker Engine and Docker Compose plugin.
    *   **Code Migration:** Clone the application repository directly onto the remote server.
    *   **Configuration:** Manually create the production `.env` file on the server (handling secrets securely).
    *   **Network Security:** Configure **AWS Security Groups** to expose Port 8000 (FastAPI) to the public internet while keeping the Database (Port 5432) internal.
    *   **Deployment:** Launch the full stack (App + DB) using `docker compose up -d` in a production environment.
*   **Deliverables:**
    *   A screenshot of the terminal showing `docker ps` with both the **App** and **Postgres** containers running on the EC2 instance.
    *   The command used to SSH into the EC2 instance.
    *   The public IP address (or URL) of the EC2 instance where the API is accessible.
    *   **Verification:** A successful Postman request to the EC2 Public IP (e.g., `/login`) confirming the API is reachable and the database is persisting data.


#### **Lab 3: Serverless Refactoring (AWS Lambda)**
**Context:** Finally, students will adapt their API for the "Serverless" era. Since Lambda doesn't listen on a port like a standard server, they need to "wrap" their FastAPI app so AWS can talk to it.

*   **Goals:**
    *   **Code Adaptation:** Install a wrapper library (like `Mangum`) and add a handler function to `main.py` so FastAPI can interpret AWS Lambda events.
    *   **Packaging:** Create a deployment package (Zip file) that includes the code and the installed dependencies (simulating a Lambda Layer).
    *   **Deployment:** Upload the package to **AWS Lambda**.
    *   **Exposure:** Configure a **Function URL** (or API Gateway) to make the Lambda function accessible via HTTP.
*   **Deliverables:**
    *   The modified `main.py` file showing the Lambda handler adapter.
    *   A screenshot of the AWS Lambda console showing the function is "Active."
    *   A working AWS Lambda URL.
    *   **Scenario Test:** The student sends a request to the Lambda URL; the function "wakes up," processes the login, returns the token, and goes back to sleep.
    
### What is Module 51 All About?

**Module 51: Deploy the Authentication API** is about moving your code from "Localhost" (your personal computer) to "Production" (the internet).

In Module 50, you built a secure API, but it only lives on your laptop. If you close your laptop, the API dies. This module teaches you three distinct ways (paradigms) to keep that API running 24/7 in the cloud:

1.  **Simple/PaaS Deployment (Poridhi Cloud):** This is usually the "easiest" method, focusing on containerizing your app and pushing it to a managed environment.
2.  **Traditional Infrastructure (AWS EC2 + RDS):** This is the industry standard for full control. You will manually set up a virtual server (EC2) and connect it to a managed professional database (RDS). This mimics how large legacy systems are often deployed.
3.  **Serverless Architecture (AWS Lambda):** This is the modern, cost-effective approach. Instead of paying for a server to run 24/7, you upload your code as a "function" that only wakes up (and costs money) when someone actually clicks a button.