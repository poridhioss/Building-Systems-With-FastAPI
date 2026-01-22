# Lab 2 – Deploying to AWS EC2

Welcome to Lab 2 of Module 51! In Lab 1, you successfully containerized your application and deployed it to Poridhi Cloud. While Poridhi Cloud is excellent for testing, in the real world, you often need to manage your own infrastructure on major cloud providers like AWS.

In this lab, you will perform a true "Lift and Shift" deployment. You will take the exact same Docker configuration you built in Lab 1—which packages your FastAPI app and PostgreSQL database—and deploy it to a live Linux server (EC2) on Amazon Web Services.

Because we are using Docker, the transition from Poridhi Cloud to AWS EC2 will be seamless. The code doesn't know the difference; it just runs.

![alt text](images/archi-diagrams/mod-50_lab-2.drawio.svg)

## Objectives

- Transfer your application code from a local environment/repo to a remote AWS server.
- Configure a production-ready Docker environment on a Linux EC2 instance.
- Manage persistent data volumes on a remote server.
- configure AWS Security Groups to allow specific traffic (Port 8000).
- Launch the application stack in detached mode for 24/7 availability.

## Prerequisites

1.  **Completed Module 51 Lab 1:** You need the containerized application code (Dockerfile, docker-compose.yml) from the previous lab.
2.  **Active AWS EC2 Instance:**
    *   You should have already launched an **Ubuntu** EC2 instance through AWS Console.
    *   You must have downloaded the `.pem` key file to your local machine.
    *   You must know the **Public IPv4 address** of your EC2 instance.
    *   *If you do not have an EC2 instance running, please pause and complete the "AWS EC2 Setup" first.*

## Step-by-Step Implementation Guide

### Step 1: Transfer Your EC2 Key to Poridhi VM

You downloaded your EC2 `.pem` key file to your local machine, but now you need it on your Poridhi VM to SSH into the EC2 instance. Since you can't directly upload files to Poridhi VM, you'll copy-paste the contents.

![alt text](./images/image.png)

**2.1 Open your .pem file on your local machine:**

On Windows, open the `.pem` file with Notepad. On Mac/Linux, use:

```bash
cat your-key-name.pem
```

Copy the entire content (including the `-----BEGIN RSA PRIVATE KEY-----` and `-----END RSA PRIVATE KEY-----` lines).

**2.2 Create the key file on Poridhi VM:**

On your Poridhi VM terminal, create a new file:

```bash
nano aws-key.pem
```

Paste the entire content you copied, then press `Ctrl+O`, `Enter` to save, and `Ctrl+X` to exit.

**2.3 Set correct permissions:**

AWS requires your key file to be read-only:

```bash
chmod 400 aws-key.pem
```

### Step 2: SSH into EC2 Instance from Poridhi VM

Now connect to your EC2 instance from the Poridhi VM. Replace `YOUR_EC2_PUBLIC_IP` with your actual EC2 public IP address:

```bash
ssh -i "aws-key.pem" ubuntu@YOUR_EC2_PUBLIC_IP
```

If asked *"Are you sure you want to continue connecting?"*, type `yes` and hit Enter. You should now see the Ubuntu welcome prompt for your EC2 instance (`ubuntu@ip-172-xx-xx-xx:~$`).

---

### Step 3: Install Docker on EC2

Your fresh EC2 instance is a blank slate. It does not have Docker or Docker Compose installed yet. We need to set up the environment.

**Important:** The following commands run on your **EC2 instance**, not the Poridhi VM.

**4.1 Update the package list:**
```bash
sudo apt-get update
```

**4.2 Install Docker:**
```bash
sudo apt-get install -y docker.io
```

**4.3 Start and Enable Docker:**
```bash
sudo systemctl start docker
sudo systemctl enable docker
```

**4.4 Grant Docker permissions to the current user:**
By default, you need `sudo` to run Docker commands. Let's fix that so we can run commands easily.
```bash
sudo usermod -aG docker $USER
```

**4.5 Install Docker Compose Plugin:**
Modern Docker includes Compose as a plugin.
```bash
sudo apt-get install -y docker-compose
```

**4.6 Apply Group Changes:**
To make the permission changes take effect without rebooting, run:
```bash
newgrp docker
```

*Verification:* Run `docker ps`. If you see an empty table (headers only) and no "permission denied" error, you are ready.

![alt text](./images/image-1.png)

---

### Step 4: Get the Application Code on EC2

**Option A: Clone from Poridhi's GitHub (Recommended)**

```bash
git clone https://github.com/poridhioss/Building-Systems-With-FastAPI.git
cd Building-Systems-With-FastAPI/
git checkout -b mod-51/lab-1 origin/mod-51/lab-1
```

**Option B: Clone your own Lab 1 code**

If you pushed your Lab 1 code to GitHub, clone your repository:

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
cd YOUR_REPO_NAME
```

---

### Step 5: Configure Environment Variables

Remember that we never commit `.env` files to Git. This means your EC2 instance currently has no idea what your secret keys or database settings are. We need to recreate the file.

**6.1 Create the file:**
```bash
nano .env
```

**6.2 Paste the configuration:**
Use the same configuration from Lab 1, but this is a chance to generate a new, stronger `JWT_SECRET`.

```env
# Application Settings
APP_NAME=FastAPI AWS EC2 Deployment

# Database Connection
# In Docker Compose, the host is the service name 'db'
DATABASE_URL=postgresql+psycopg2://postgres:postgres@db:5432/auth_lab1_db

# JWT Configuration - KEEP THIS SECRET!
# Generate a secure secret: openssl rand -hex 32
JWT_SECRET=your-super-secret-key-change-this-in-production-min-32-chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
```

**6.3 Save and Exit:**
Press `Ctrl+O`, `Enter` to save, then `Ctrl+X` to exit.

---

### Step 6: Verify Docker Compose Configuration

Let's quickly verify our `docker-compose.yml` matches our AWS needs. Since we are running the DB in a container (not RDS), the file from Lab 1 should work perfectly without changes.

Check the file content:
```bash
cat docker-compose.yml
```

Ensure the database service is defined and the app depends on it. It should look like this:

```yaml
version: "3.9"
services:
  db:
    image: postgres:16
    container_name: auth_postgres
    # ... (postgres config)
  app:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
```

---

### Step 7: Build and Launch

Now comes the magic of "Lift and Shift." Because we have a Dockerfile, we don't need to install Python, Virtual Environments, or Pip on the EC2 instance directly. Docker handles it all.

**7.1 Build the images:**
```bash
docker compose build
```
*Note: This might take a minute or two as the EC2 instance downloads the Python base image and installs dependencies.*

**7.2 Run the stack in Detached Mode:**
```bash
docker-compose up -d
```

**7.3 Verify Deployment:**
Check that containers are running:
```bash
docker-compose ps
```

![alt text](./images/image-2.png)

You should see `auth_fastapi` and `auth_postgres` with Status "Up".

You can also check the logs:
```bash
docker-compose logs app
```

![alt text](./images/image-3.png)

You should see Alembic migrations running and uvicorn starting successfully.

---

### Step 8: Configure AWS Security Group

Your application is running on the server, but AWS puts a "Firewall" around your EC2 instance by default. It usually allows SSH (Port 22), but blocks everything else. We need to open Port **8000**.

1.  Go to the **AWS Console** in your browser.
2.  Navigate to **EC2** > **Instances**.
3.  Select your instance.
4.  Click the **Security** tab in the bottom details pane.
5.  Click the **Security Group ID** (e.g., `sg-01234abc...`).
6.  Click **Edit inbound rules**.
7.  Click **Add rule**:
    *   **Type:** Custom TCP
    *   **Port range:** `8000`
    *   **Source:** Anywhere-IPv4 (`0.0.0.0/0`)
8.  Click **Save rules**.

![alt text](./images/image-4.png)

---

### Step 9: Test Your Deployed Application with Postman

Now your API is live and accessible directly via the EC2 public IP! Unlike Lab 1, you don't need a Poridhi Load Balancer - you're accessing the EC2 instance directly.

**9.1 Get your Public IP:**

Go to the EC2 Instances dashboard in AWS Console and copy the **Public IPv4 address** of your instance.

**9.2 Quick health check:**

Open a browser and navigate to:
```
http://YOUR_EC2_PUBLIC_IP:8000/ping
```

You should see: 

![alt text](./images/image-5.png)

**9.3 Comprehensive Postman Tests:**

Open Postman on your local machine. We'll test the complete authentication flow. Throughout these tests, replace `YOUR_EC2_PUBLIC_IP` with your actual EC2 public IP address.

**Test 1: Register a new user**

![alt text](./images/image-6.png)

Create a new POST request in Postman:
- **Method**: POST
- **URL**: `http://YOUR_EC2_PUBLIC_IP:8000/register`
- **Headers**:
  - `Content-Type`: `application/json`
- **Body** (select "raw" and "JSON"):

```json
{
  "email": "aws@example.com",
  "password": "AWSPassword123!"
}
```

Click "Send". You should get a 201 response with the user details.

![alt text](./images/image-7.png)

**Test 2: Login**

![alt text](./images/image-8.png)

Create a new POST request:
- **Method**: POST
- **URL**: `http://YOUR_EC2_PUBLIC_IP:8000/login`
- **Headers**:
  - `Content-Type`: `application/json`
- **Body** (raw JSON):

```json
{
  "email": "aws@example.com",
  "password": "AWSPassword123!"
}
```

Click "Send". You'll receive both access and refresh tokens in the response. Copy the `access_token` value - you'll need it for the next test.

![alt text](./images/image-9.png)

**Test 3: Access protected endpoint**

Create a new GET request:
- **Method**: GET
- **URL**: `http://YOUR_EC2_PUBLIC_IP:8000/users/me`
- **Headers**:
  - `Authorization`: `Bearer <paste-your-access-token-here>`

![alt text](./images/image-10.png)

Make sure to include the word "Bearer" followed by a space, then your access token.

Click "Send". You should see your user information in the response.

![alt text](./images/image-11.png)

**Test 4: Test refresh token**

![alt text](./images/image-12.png)

Create a new POST request:
- **Method**: POST
- **URL**: `http://YOUR_EC2_PUBLIC_IP:8000/refresh`
- **Headers**:
  - `Content-Type`: `application/json`
- **Body** (raw JSON):

```json
{
  "refresh_token": "paste-your-refresh-token-here"
}
```

Click "Send". You should get a new access token back.

![alt text](./images/image-13.png)

**Test 5: Test logout**

![alt text](./images/image-14.png)

Create a new POST request:
- **Method**: POST
- **URL**: `http://YOUR_EC2_PUBLIC_IP:8000/logout`
- **Headers**:
  - `Content-Type`: `application/json`
- **Body** (raw JSON):

```json
{
  "refresh_token": "paste-your-refresh-token-here"
}
```

Click "Send". You should see a success message saying you've been logged out.

![alt text](./images/image-15.png)

**Test 6: Verify token revocation**

![alt text](./images/image-16.png)

Try to use the `/refresh` endpoint again with the same refresh token. You should get a 401 error saying "Refresh token has been revoked".

Congratulations! Your application is running on AWS EC2 and all authentication endpoints work correctly.

---

### Step 10: Persistence Test (The "Crash" Simulation)

One of the benefits of Docker volumes is data persistence. Let's prove that your data survives a server restart.

1.  **Stop the containers:**
    ```bash
    docker-compose down
    ```
    *This stops and removes the containers, simulating a crash or update.*

2.  **Start them again:**
    ```bash
    docker-compose up -d
    ```

3.  **Check Data:**
    Use Postman to **Login** again with the user you created in Step 10.
    *   **Result:** It should work! Even though the container was destroyed, the data lived on in the `pgdata` Docker volume.


![alt text](./images/image-17.png) 

---

### Conclusion

Congratulations! You've successfully deployed your containerized application to AWS EC2, experiencing true infrastructure-as-a-service (IaaS) deployment. The exact same Docker configuration from Lab 1 worked seamlessly on AWS, demonstrating the power of containerization and portability. You learned how to provision and configure a raw Linux server, install Docker runtime, manage SSH access from a Poridhi VM, configure AWS Security Groups for network access, and verify data persistence across container restarts. Unlike Poridhi Cloud's managed environment, you now have full control over the infrastructure, which is how most production systems are deployed. In Lab 3, you'll adapt this application for serverless deployment on AWS Lambda, completing your understanding of modern cloud deployment strategies.