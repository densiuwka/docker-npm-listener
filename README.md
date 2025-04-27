# Docker Event Listener for NPM Proxy Host Automation

A Python-based service that listens to Docker container lifecycle events and automatically creates proxy hosts in [Nginx Proxy Manager (NPM)](https://nginxproxymanager.com/) when new containers start. Notifications about operations can be sent via [ntfy](https://ntfy.sh/).

---

## Features

- Listens to Docker container **start** events.
- Automatically creates new proxy hosts in Nginx Proxy Manager based on container labels.
- Uses environment variables for easy configuration.
- Sends notifications for token acquisition and proxy creation via NTFY.
- Runs as a reliable background service with graceful shutdown and robust error handling.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
- [Usage](#usage)
- [Running as a Service](#running-as-a-service)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Prerequisites

- Docker installed and running on your Docker host.
- Nginx Proxy Manager API accessible with an API user.
- Access to a NTFY server/topic for notifications (optional).
- Python 3.8+ installed.

---

## Configuration

Create a `.env` file in the project root with the following environment variables:

```env
USE_NTFY_FOR_UPDATES=...
NTFY_SERVER_URL=...
NTFY_TOPIC=...
HOST_IP_ADDRESS=...
DOCKER_PORT=...
NPM_SERVER_URL=...
NPM_USER=...
NPM_SECRET=...
```
See [example .env file](dotenv%20example) for more details.

**Note:**  
- `npmdocker.host`, `npmdocker.port` and `npmdocker.tls.domain` labels must be set on your Docker containers. Example:

```yaml
labels:
   - "npmdocker.host=website.example.com" # Forwarded host
   - "npmdocker.port=8080" # Forwarded port
   - "npmdocker.tls.domain=example.com" # Your cert domain
```
- Your NPM API user must have permission to create proxy hosts via the API.

---

## Usage

To run the event listener manually:

```bash
python3 main.py
```

- The script listens indefinitely for container start events and processes them.  
- Logs are printed with timestamps, so you can monitor the activity easily.

It is recommended to run [install script](install.sh) for automated installation that will walk you through the setup:

```bash
sudo bash install.sh
```
Alternatively, follow the steps in [Running as a Service](#running-as-a-service) to set up a `systemd` service. In this case remember to configure Python with all ot the necessary requirements:

1. Create a Python virtual environment and activate it (recommended, but optional):

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

---

## Running as a Service

To run this script as a background service using `systemd`:

1. Create a systemd service file `/etc/systemd/system/docker-npm-listener.service`:

   ```ini
   [Unit]
   Description=Docker Event Listener for NPM Proxy Automation
   After=docker.service
   Requires=docker.service

   [Service]
   ExecStart=/path/to/your/venv/bin/python /path/to/your/project/main.py
   Restart=always
   User=youruser
   Group=yourgroup
   WorkingDirectory=/path/to/your/project
   Nice=10
   CPUWeight=512
   MemoryMax=256M
   EnvironmentFile=/path/to/your/project/.env

   [Install]
   WantedBy=multi-user.target
   ```

2. Reload systemd config:

   ```bash
   sudo systemctl daemon-reload
   ```

3. Enable and start the service:

   ```bash
   sudo systemctl enable docker-npm-listener
   sudo systemctl start docker-npm-listener
   ```

4. Check service status and logs:

   ```bash
   sudo systemctl status docker-npm-listener
   sudo journalctl -u docker-npm-listener -f
   ```

---

## Troubleshooting

- Make sure Docker daemon is running and user has permission to access Docker socket (`/var/run/docker.sock`).  
- Verify that the `.env` file has correct values and is readable by your script/service user.  
- Check system logs (`journalctl`) for detailed error messages.  
- If proxy hosts are not created, verify container labels `npmdocker.host` and `npmdocker.port`.  
- For authentication issues with NPM, confirm API credentials and permissions.

---

## License

This project is licensed under the GNU GPL v3.0 License. See the [LICENSE](LICENSE) file for details.

---

## Contributions and Feedback

Feel free to open issues or pull requests to improve this project!  
Your feedback and contributions are welcomed.

---

*Happy automating with Docker and Nginx Proxy Manager!* 🚀