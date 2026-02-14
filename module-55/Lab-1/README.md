# Lab 1: Monitoring Celery Workers with Flower

In Module 54, you built a production-ready task queue with automatic retries, timeout enforcement, comprehensive logging, and structured error handling. Your Flask-Celery application can now handle failures gracefully and prevent runaway tasks from consuming resources. But there's a critical missing piece: **real-time visibility**.

When you're running Celery workers in production, you need to answer questions like:
- Which tasks are currently executing?
- How many tasks succeeded vs. failed in the last hour?
- Why did this specific task fail? What was the exception?
- Are tasks piling up faster than workers can process them?
- Is Worker-2 slower than Worker-1? Why?
- Which tasks are being retried, and how many times?

Without a monitoring tool, you'd have to grep through log files, manually query Redis, or write custom database queries. This is tedious, error-prone, and doesn't give you real-time insights.

**Flower** solves this problem. It's a real-time web-based monitoring and administration tool for Celery that provides:
- Live task state tracking (PENDING → STARTED → SUCCESS/FAILURE/RETRY)
- Worker health monitoring (active workers, CPU usage, memory)
- Task history with searchable filters (status, task name, time range)
- Exception tracebacks for failed tasks
- Task arguments and return values
- Queue length and backlog metrics
- Task routing visualization

In this lab, you'll install Flower, connect it to your existing Flask-Celery app from Module 54, and learn how to use its dashboard to monitor task execution in real-time. You'll trigger tasks with different outcomes (success, failure, timeout, retry) and observe how Flower visualizes each state transition.

## Architecture Diagram

Flower sits alongside your existing Flask-Celery infrastructure and reads data from the Redis broker and result backend:

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client (curl/browser)                    │
└────────┬───────────────────────────────────────┬────────────────┘
         │                                       │
         │ HTTP POST /register                   │ HTTP GET :5555
         │ (Trigger tasks)                       │ (Monitor tasks)
         ▼                                       ▼
┌──────────────────────┐              ┌─────────────────────────┐
│   Flask Application  │              │   Flower Dashboard      │
│   (Port 5000)        │              │   (Port 5555)           │
│                      │              │                         │
│  - POST /register    │              │  - Tasks page           │
│  - POST /reports     │              │  - Workers page         │
│  - GET /tasks/:id    │              │  - Monitor page         │
└──────────┬───────────┘              └────────┬────────────────┘
           │                                   │
           │ Queue task                        │ Read task data
           │                                   │ Read worker data
           ▼                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Redis (Port 6379)                          │
│  ┌────────────────────────┐  ┌────────────────────────────┐    │
│  │  Database 0 (Broker)   │  │  Database 1 (Result Backend)│   │
│  │  - Task queue          │  │  - Task states             │    │
│  │  - Pending tasks       │  │  - Task results            │    │
│  └────────────────────────┘  └────────────────────────────┘    │
└────────────┬────────────────────────────────────────────────────┘
             │
             │ Poll for tasks
             │ Write results
             ▼
┌─────────────────────────┐
│   Celery Worker         │
│   (Background Process)  │
│                         │
│  - Executes tasks       │
│  - Handles retries      │
│  - Enforces timeouts    │
└─────────────────────────┘
```

**Key Points:**
- **Flask API** and **Flower** are separate processes that both connect to Redis
- **Flower** reads from the broker (to see queued tasks) and the result backend (to see task states/results)
- **Flower** does NOT execute tasks—it's purely a monitoring/inspection tool
- Clients can trigger tasks via Flask and immediately switch to Flower to watch them execute

## Objectives

By the end of this lab, you will:

1. Install Flower and understand its role in the Celery monitoring ecosystem
2. Launch the Flower web dashboard and connect it to your Redis broker
3. Monitor tasks in real-time as they transition through states (PENDING → STARTED → SUCCESS)
4. Inspect task details: arguments, return values, execution time, worker assignment
5. View exception tracebacks for failed tasks directly in the Flower UI
6. Observe retry attempts and timeout terminations in the task timeline
7. Monitor worker health: active workers, concurrency, processed task count
8. Use Flower's search and filter features to find specific tasks
9. (Optional) Secure the Flower dashboard with basic authentication
10. (Optional) Deploy Flower behind Nginx as a reverse proxy for production use

## Prerequisites

This lab builds directly on Module 54 Lab 1. You should have:
- A working Flask-Celery application with retry, timeout, and error handling
- Redis running via Docker Compose
- The following tasks defined: `send_welcome_email`, `generate_monthly_report`, `flaky_task`, `slow_task`

If you haven't completed Module 54, go back and complete it first. We'll be using that exact project structure.

## Project Structure

We're extending the Module 54 project. The structure will look like this:

```
flask-celery-app/
├── app/
│   ├── __init__.py
│   ├── routes.py
│   └── tasks.py
├── celery_utils.py
├── config.py
├── docker-compose.yml
├── requirements.txt       # Updated with Flower
├── run.py
├── start_flower.sh        # New: Flower startup script
└── .venv/
```

The only new file is `start_flower.sh`, which launches the Flower dashboard. Everything else remains unchanged.

## Step 1: Install Flower

First, navigate to your Module 54 project directory:

```bash
cd flask-celery-app
source .venv/bin/activate
```

Install Flower:

```bash
pip install flower==2.0.1
```

**What is Flower?**
- A web-based tool for monitoring and administering Celery clusters
- Provides real-time visibility into task execution and worker health
- Displays task states, arguments, results, and exception tracebacks
- Shows queue lengths, worker concurrency, and task routing
- Written in Python using Tornado web framework

Update your `requirements.txt` to include Flower:

```bash
echo "flower==2.0.1" >> requirements.txt
```

Your `requirements.txt` should now contain:

```txt
flask==3.0.0
celery==5.3.4
redis==5.0.1
flower==2.0.1
```

## Step 2: Start Your Existing Infrastructure

Before launching Flower, make sure your Flask-Celery app from Module 54 is running. You'll need three terminals:

**Terminal 1: Start Redis**

```bash
cd flask-celery-app
docker compose up -d
```

Verify Redis is running:

```bash
docker ps
```

You should see the `flask-celery-redis` container.

**Terminal 2: Start the Celery Worker**

```bash
source .venv/bin/activate
celery -A app.celery worker --loglevel=info
```

Wait until you see the `[ready]` message indicating the worker is waiting for tasks.

**Terminal 3: Start the Flask Application**

```bash
source .venv/bin/activate
python run.py
```

The Flask app should start on `http://127.0.0.1:5000`.

At this point, you have the full infrastructure running. Now let's add Flower to monitor it.

## Step 3: Launch the Flower Dashboard

Open a **fourth terminal** and launch Flower:

```bash
cd flask-celery-app
source .venv/bin/activate

# Launch Flower
celery -A app.celery flower --port=5555
```

**What this command does:**
- `-A app.celery`: Tells Flower to connect to the Celery instance defined in `app/__init__.py`
- `flower`: Launches Flower instead of a worker
- `--port=5555`: Runs the Flower web UI on port 5555 (the default Flower port)

You should see output similar to this:

```
[I 2026-02-07 10:30:15,123] Starting Flower version 2.0.1
[I 2026-02-07 10:30:15,234] Broker: redis://localhost:6379/0
[I 2026-02-07 10:30:15,345] Registered tasks:
    ['app.tasks.flaky_task',
     'app.tasks.generate_monthly_report',
     'app.tasks.send_welcome_email',
     'app.tasks.slow_task']
[I 2026-02-07 10:30:15,456] Flower listening on http://localhost:5555
```

**Important:** Keep this terminal open. Flower needs to stay running to monitor your tasks.

## Step 4: Access the Flower Dashboard

Open your web browser and navigate to:

```
http://localhost:5555
```

You should see the Flower homepage with several tabs:

![Flower Dashboard Home](images/image.png)

**Main Dashboard Sections:**

1. **Tasks**: Shows all tasks with their states, execution times, and results
2. **Workers**: Displays active workers, their concurrency, and task counts
3. **Monitor**: Real-time task timeline showing when tasks start and complete
4. **Broker**: Shows broker connection details and queue information
5. **Task Details**: Click any task to see arguments, results, and tracebacks

Initially, the dashboard will be mostly empty because you haven't triggered any tasks yet. Let's change that.

## Step 5: Trigger Tasks and Monitor in Real-Time

Now comes the exciting part—watching tasks execute in real-time. Open a **fifth terminal** for triggering tasks:

```bash
# Terminal 5: Task triggering
cd flask-celery-app
```

### Test 1: Monitor a Successful Task

Trigger a successful task:

```bash
curl -X POST http://localhost:5000/register \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com"}'
```

You'll get an instant response with a task ID:

```json
{
  "message": "User registered. Welcome email is being sent in the background.",
  "task_id": "a1b2c3d4-5678-90ef-ghij-klmnopqrstuv"
}
```

**Immediately switch to your browser with Flower open.** Click on the **Tasks** tab.

![Task List View](images/image-1.png)

You should see:
- **Task Name**: `app.tasks.send_welcome_email`
- **State**: Initially `PENDING`, then `STARTED`, then `SUCCESS`
- **Runtime**: The task execution time (should be around 5 seconds)
- **Worker**: Which worker executed the task (e.g., `celery@hostname`)

Click on the task to see detailed information:

![Task Details](images/image-2.png)

You'll see:
- **Arguments**: `('alice@example.com',)` - the email address you passed
- **Result**: The return value (e.g., `"Welcome email sent to alice@example.com"`)
- **State**: `SUCCESS`
- **Received**: Timestamp when the task was queued
- **Started**: Timestamp when the worker picked it up
- **Succeeded**: Timestamp when it completed

This is incredibly valuable for debugging—you can see exactly what arguments were passed and what the task returned.

### Test 2: Monitor a Failing Task with Retries

Now trigger the flaky task that randomly fails:

```bash
curl -X POST http://localhost:5000/test-reliability
```

Switch to Flower and watch the **Monitor** tab (this shows a real-time timeline):

![Monitor Timeline](images/image-3.png)

Since `flaky_task` fails 70% of the time, you'll likely see:

1. **First attempt**: Task starts, fails after 2 seconds
2. **State changes to RETRY**: Flower shows the task in orange/yellow
3. **Wait period**: The task waits for the exponential backoff delay (5s → 10s → 20s)
4. **Second attempt**: Task starts again
5. **Possible outcomes**:
   - If it fails again: Another RETRY, wait longer
   - If it succeeds: State changes to SUCCESS

Click on the task in the Tasks tab to see the retry history:

![Retry History](images/image-4.png)

You'll see:
- **Retries**: How many times it was retried (e.g., `2/3`)
- **Exception**: The error message from the failed attempt: `"Simulated random failure"`
- **Traceback**: Full Python stack trace showing where the error occurred

This is exactly what you need when debugging production issues—you can see the exception without digging through log files.

### Test 3: Monitor a Task That Times Out

Trigger the slow task that exceeds its timeout:

```bash
curl -X POST http://localhost:5000/test-timeout \
  -H "Content-Type: application/json" \
  -d '{"duration": 20}'
```

Switch to the Flower Tasks tab:

![Timeout Task](images/image-5.png)

You'll observe:
1. Task starts and shows `STARTED` state
2. After 12 seconds (the `soft_time_limit`), the task catches the timeout
3. Task state changes to `SUCCESS` with result: `{"status": "timeout", "message": "Task exceeded time limit"}`

The beauty of Flower is that you can see this entire lifecycle in real-time without checking worker logs.

**Challenge:** Trigger a task that exceeds the hard timeout (30+ seconds). You'll see the state change to `FAILURE` with the exception `TimeLimitExceeded`.

## Step 6: Explore the Workers Page

Click on the **Workers** tab in Flower:

![Workers Page](images/image-6.png)

Here you'll see critical information about your Celery workers:

**Worker Information:**
- **Hostname**: The worker's identifier (e.g., `celery@my-vm`)
- **Status**: Online/Offline
- **Active Tasks**: Tasks currently being executed by this worker
- **Processed**: Total number of tasks processed since the worker started
- **Concurrency**: Number of parallel processes (should match what you saw when starting the worker)
- **Uptime**: How long the worker has been running

**Why This Matters:**

In production, you might have multiple workers on different machines. The Workers page lets you:
- Verify all workers are online and healthy
- Identify slow workers (low processed count compared to others)
- Check if tasks are distributed evenly across workers
- See which workers are currently busy vs. idle

**Try This:** In your Celery worker terminal (Terminal 2), press `Ctrl+C` to stop the worker. Then refresh the Flower Workers page. You'll see the worker status change to "Offline". Restart the worker and watch it come back online.

## Step 7: Use the Task Search and Filter

The Tasks page has powerful search and filtering capabilities. Let's explore them.

Trigger several tasks:

```bash
# Send 5 welcome emails
for i in {1..5}; do
  curl -X POST http://localhost:5000/register \
    -H "Content-Type: application/json" \
    -d "{\"email\": \"user$i@example.com\"}"
  sleep 1
done

# Generate 3 reports
for i in {1..3}; do
  curl -X POST http://localhost:5000/reports/generate \
    -H "Content-Type: application/json" \
    -d "{\"user_id\": $i}"
  sleep 1
done

# Trigger 3 flaky tasks
for i in {1..3}; do
  curl -X POST http://localhost:5000/test-reliability
  sleep 1
done
```

Now in Flower, go to the Tasks tab and use the filters:

![Task Filters](images/image-7.png)

**Available Filters:**

1. **State Filter**: Show only tasks with specific states
   - Click "SUCCESS" to see only successful tasks
   - Click "FAILURE" to see only failed tasks
   - Click "RETRY" to see tasks that are being retried

2. **Task Name Filter**: Filter by task type
   - Select `app.tasks.send_welcome_email` to see only email tasks
   - Select `app.tasks.generate_monthly_report` to see only report tasks

3. **Time Range**: Filter by when tasks were executed
   - Last hour, last 24 hours, custom range

4. **Search Box**: Search by task ID, arguments, or result values

**Try This:**
- Filter to show only `FAILURE` tasks—you'll see the flaky tasks that exhausted retries
- Click on a failed task to see the full exception traceback
- Use the search box to search for a specific email address (e.g., `user3@example.com`)

This is extremely useful in production when you're trying to find a specific failed task among thousands of completed ones.

## Step 8: Understanding Task States in Flower

Flower displays tasks in different states. Here's what each state means:

| State | Color | Meaning |
|-------|-------|---------|
| **PENDING** | Gray | Task is queued but not yet picked up by a worker |
| **STARTED** | Blue | Worker is currently executing the task |
| **SUCCESS** | Green | Task completed successfully |
| **FAILURE** | Red | Task failed with an unhandled exception |
| **RETRY** | Orange/Yellow | Task failed but will be retried |
| **REVOKED** | Purple | Task was cancelled before execution |

**State Transitions:**

Normal successful task:
```
PENDING → STARTED → SUCCESS
```

Task with retries:
```
PENDING → STARTED → RETRY → PENDING → STARTED → SUCCESS
```

Task that fails permanently:
```
PENDING → STARTED → RETRY → PENDING → STARTED → RETRY → PENDING → STARTED → FAILURE
```

Task that times out:
```
PENDING → STARTED → FAILURE (TimeLimitExceeded)
```

Understanding these states is crucial for debugging production issues.

## Step 9: Monitor Queue Length and Backlog

One of the most important production metrics is queue backlog—are tasks piling up faster than workers can process them?

Let's create a backlog intentionally. First, stop your Celery worker (in Terminal 2, press `Ctrl+C`).

Now queue up a bunch of tasks:

```bash
# Queue 20 tasks while the worker is offline
for i in {1..20}; do
  curl -X POST http://localhost:5000/register \
    -H "Content-Type: application/json" \
    -d "{\"email\": \"user$i@example.com\"}"
done
```

In Flower, click on the **Broker** tab:

![Broker Queue Stats](images/image-8.png)

You'll see:
- **Messages in Queue**: 20 (the tasks you just queued)
- **Messages Delivered**: 0 (no worker to deliver them to)
- **Queue Name**: `celery` (the default queue)

This tells you tasks are piling up. In production, this would be a red flag—you might need to scale up workers.

Now restart your worker:

```bash
# In Terminal 2
celery -A app.celery worker --loglevel=info
```

Watch the Flower Broker tab. You'll see the queue length drop rapidly as the worker processes tasks.

**Production Use Case:** Set up alerts based on queue length. If the queue exceeds a threshold (e.g., 100 tasks), automatically scale up workers or send an alert to your on-call engineer.

## Step 10: Task Routing and Pool Configuration

Flower also shows you how tasks are routed and which execution pool is being used.

In the Workers tab, click on your worker name to see detailed configuration:

![Worker Configuration](images/image-9.png)

You'll see:
- **Pool Type**: `prefork` (the default, uses multiple processes)
- **Pool Size**: Number of concurrent worker processes (e.g., 4)
- **Max Tasks Per Child**: How many tasks a worker process handles before restarting
- **Registered Queues**: Which queues this worker is listening to

**Why This Matters:**

Different tasks have different requirements:
- **CPU-bound tasks** (image processing, PDF generation): Use `prefork` pool for true parallelism
- **I/O-bound tasks** (API calls, file uploads): Use `gevent` or `eventlet` pool for concurrency
- **Long-running tasks**: Set `max_tasks_per_child` to prevent memory leaks

Flower lets you verify your worker configuration without SSHing into production servers.

## Step 11: (Optional) Secure Flower with Basic Authentication

By default, Flower has no authentication—anyone who can access port 5555 can see all your tasks. In production, you should secure it.

Stop your Flower process (in Terminal 4, press `Ctrl+C`).

Restart Flower with basic authentication:

```bash
celery -A app.celery flower \
  --port=5555 \
  --basic_auth=admin:securepassword123
```

Now when you navigate to `http://localhost:5555`, you'll be prompted for credentials:

![Flower Login](images/image-10.png)

Enter:
- **Username**: `admin`
- **Password**: `securepassword123`

**For Multiple Users:**

```bash
celery -A app.celery flower \
  --port=5555 \
  --basic_auth=admin:password123,developer:devpass456
```

This allows both `admin:password123` and `developer:devpass456` to log in.

**Important:** Basic auth over HTTP sends passwords in base64 (easily decoded). In production, you should:
1. Use HTTPS (TLS/SSL) to encrypt traffic
2. Run Flower behind a reverse proxy (Nginx) with proper SSL certificates
3. Use a firewall to restrict access to Flower's port

## Step 12: (Optional) Deploy Flower Behind Nginx

For production deployments, you should run Flower behind a reverse proxy like Nginx. This allows you to:
- Add SSL/TLS encryption
- Implement IP-based access control
- Serve Flower on a custom domain (e.g., `https://flower.yourcompany.com`)
- Load balance across multiple Flower instances

Create an Nginx configuration file `flower-nginx.conf`:

```nginx
server {
    listen 80;
    server_name flower.yourcompany.com;

    # Redirect HTTP to HTTPS (in production, use SSL)
    # return 301 https://$server_name$request_uri;

    location / {
        proxy_pass http://localhost:5555;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support for real-time updates
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # IP-based access control (optional)
    # allow 192.168.1.0/24;  # Your office network
    # deny all;
}
```

Install and configure Nginx:

```bash
sudo apt update
sudo apt install nginx -y

# Copy the config
sudo cp flower-nginx.conf /etc/nginx/sites-available/flower
sudo ln -s /etc/nginx/sites-available/flower /etc/nginx/sites-enabled/

# Test and reload
sudo nginx -t
sudo systemctl reload nginx
```

Now you can access Flower via `http://your-server-ip` instead of `http://your-server-ip:5555`.

**For SSL/TLS:** Use Let's Encrypt to get a free SSL certificate:

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d flower.yourcompany.com
```

This automatically configures Nginx with SSL and redirects HTTP to HTTPS.

## Step 13: Create a Startup Script for Flower

For convenience, create a shell script to launch Flower with your preferred settings.

Create `start_flower.sh`:

```bash
#!/bin/bash

# Activate virtual environment
source .venv/bin/activate

# Launch Flower with authentication and custom port
celery -A app.celery flower \
  --port=5555 \
  --basic_auth=admin:securepassword123 \
  --max_tasks=10000 \
  --persistent=True \
  --db=/tmp/flower.db
```

**What these options do:**
- `--max_tasks=10000`: Keep the last 10,000 tasks in memory (default is 10,000)
- `--persistent=True`: Persist task history to a database
- `--db=/tmp/flower.db`: SQLite database file for persistence

Make it executable:

```bash
chmod +x start_flower.sh
```

Run it:

```bash
./start_flower.sh
```

Now you have a single command to launch Flower with all your preferred settings.

## Best Practices for Using Flower in Production

Based on your experience in this lab, here are key best practices:

### 1. Always Use Authentication
- Never expose Flower without authentication in production
- Use `--basic_auth` at minimum
- Consider integrating with your company's OAuth/SSO for enterprise deployments

### 2. Limit Task History
- Set `--max_tasks` to prevent memory bloat (10,000-50,000 is reasonable)
- Enable persistence (`--persistent=True`) to survive Flower restarts
- Regularly archive old task data to a separate monitoring system

### 3. Restrict Network Access
- Don't expose Flower directly to the internet
- Use a VPN or IP whitelist to restrict access
- Run behind a reverse proxy with SSL/TLS

### 4. Monitor Flower Itself
- Flower is just another Python process—it can crash
- Use a process supervisor like `systemd` or `supervisord` to auto-restart it
- Set up alerts if Flower becomes unavailable

### 5. Use Flower for Debugging, Not Long-Term Storage
- Flower is a real-time monitoring tool, not a long-term analytics platform
- For historical analysis, export task data to a proper database or logging system
- Consider tools like Grafana, Prometheus, or ELK stack for long-term metrics

### 6. Scale Flower for Large Deployments
- For high-traffic systems (100+ tasks/second), run multiple Flower instances
- Use Redis Sentinel or Redis Cluster for high-availability broker setup
- Consider dedicated monitoring workers that only inspect tasks without executing them

## Common Flower Troubleshooting

### Issue 1: Flower Shows No Tasks

**Symptoms:** The Tasks page is empty even though you're triggering tasks.

**Possible Causes:**
1. Flower is connected to the wrong Redis database
2. Tasks are being sent to a different broker than Flower is monitoring
3. The result backend is not configured

**Solution:**
- Check that Flower's `-A` parameter points to the correct Celery app
- Verify the broker URL matches your Celery configuration
- Ensure `result_backend` is configured in your Celery settings

### Issue 2: Workers Show as Offline

**Symptoms:** The Workers page shows no active workers.

**Possible Causes:**
1. Worker is not running
2. Worker is connected to a different broker
3. Firewall blocking connections

**Solution:**
- Verify the worker is running: `ps aux | grep celery`
- Check worker and Flower are using the same broker URL
- Test broker connectivity: `redis-cli ping`

### Issue 3: Task Details Missing

**Symptoms:** Task shows in the list but clicking it shows no details.

**Possible Causes:**
1. Result backend not configured
2. Task completed before backend was set up
3. Result expired (Redis TTL)

**Solution:**
- Ensure `result_backend` is configured in Celery settings
- Check `result_expires` setting (default is 24 hours)
- For critical tasks, increase `result_expires` or use a permanent database backend

## Summary

In this lab, you added real-time monitoring to your Flask-Celery application using Flower. You learned how to:

1. **Install and launch Flower** to monitor your existing Celery infrastructure
2. **Monitor tasks in real-time** as they transition through states (PENDING → STARTED → SUCCESS/FAILURE/RETRY)
3. **Inspect task details** including arguments, return values, exception tracebacks, and retry history
4. **Track worker health** with active worker counts, concurrency settings, and task processing stats
5. **Filter and search tasks** to find specific executions in large task histories
6. **Monitor queue backlogs** to identify when workers are falling behind
7. **Secure the dashboard** with basic authentication and reverse proxy setup

Flower transforms your Celery cluster from a black box into a transparent, observable system. When tasks fail in production at 2am, instead of grepping through gigabytes of logs, you can open Flower, filter to failed tasks, and immediately see the exception traceback and input arguments.

**Key Takeaways:**

- **Flower is read-only**: It monitors tasks but doesn't execute them
- **Real-time visibility**: See tasks transition through states as they happen
- **Debug-friendly**: Exception tracebacks, arguments, and results all in one place
- **Production-ready**: With proper authentication and reverse proxy setup
- **Scalable**: Can monitor clusters with hundreds of workers and millions of tasks

However, Flower has limitations. It only shows you what's happening inside your Celery system. It doesn't show you the bigger picture:
- How long did the entire user request take (API + task)?
- If a task calls an external API, how much time was spent waiting vs. processing?
- How do tasks interact with your database?

To answer these questions, you need **distributed tracing**—a technique that tracks requests across multiple services and shows you the complete execution timeline. That's exactly what we'll build in Module 56 with Grafana Tempo and OpenTelemetry.
