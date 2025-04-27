import docker
import logging
import os
import signal
import time
from npm_integration import NpmIntegration as npm
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s %(levelname)s %(message)s"
)

# Handle shutting down of the process
running = True
def shutdown(signum, frame):
    global running
    logging.info(f"Received signal {signum}, shutting down...")
    running = False

signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)

# Load environment variables
dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')

if not os.path.isfile(dotenv_path):
    err_msg = f"Error: .env file not found at expected path: {dotenv_path}"
    logging.error(err_msg)
    raise FileNotFoundError(err_msg)
if os.path.getsize(dotenv_path) == 0:
    err_msg = f"Error: .env file at {dotenv_path} is empty"
    logging.error(err_msg)
    raise ValueError(err_msg)

load_dotenv()

def wait_for_labels(container, timeout=10):
    """
    Poll container labels until expected labels appear or timeout
    """
    start = time.time()
    while time.time() - start < timeout:
        try:
            container.reload()
            labels = container.labels
            if labels.get("npmdocker.host") and labels.get("npmdocker.port") and labels.get("npmdocker.tls.domain"):
                return labels
        except Exception as e:
            logging.warning(f"Error reloading container: {e}")
        time.sleep(0.5)
    return None

def main():
    client = docker.from_env()
    event_stream = client.events(decode=True)
    logging.info("Started Docker Event Listener...")
    
    while running:
        try:
            event = next(event_stream)
            if event["Type"] == "container" and event["Action"] == "start":
                container_id = event["Actor"]["ID"]
                container = client.containers.get(container_id)
                container_name = container.name
                logging.info(f"New container found! ID: {container_name} ({container_id}). Searching for name and port...")
                
                labels = wait_for_labels(container)
                if not labels:
                    logging.warning(f"Container {container_name} ({container_id}) missing labels for NPM proxy. Skipping.")
                    continue
                
                proxy_host = labels.get("npmdocker.host")
                proxy_port = labels.get("npmdocker.port")
                proxy_domain = labels.get("npmdocker.tls.domain")
                
                if not proxy_host or not proxy_port or not proxy_domain:
                    logging.warning(f"Some labels for container {container_name} ({container_id}) are empty, skipping.")
                    continue
                
                # Ensure port is int
                try:
                    proxy_port = int(proxy_port)
                except ValueError:
                    logging.error(f"Invalid port value '{proxy_port}' for container {container_name} ({container_id}). Skipping.")
                    continue
                
                logging.info(f"Creating NPM Proxy Host. Host: {proxy_host}. Port: {proxy_port}")
                
                proxy_cert_id = npm.get_cert_id(proxy_domain)
                if proxy_cert_id is None:
                    logging.warning(f"Certificate ID not found for domain {proxy_domain}. Defaulting to cert_id = 1.")
                    proxy_cert_id = 1
                
                success = npm.create_npm_proxy_host(proxy_host, proxy_port, proxy_cert_id)
                if not success:
                    logging.error(f"Failed to create NPM proxy host for container {container_name} ({container_id})")
                
                logging.info("Listening for new containers...")
        except StopIteration:
            break
        except Exception as e:
            logging.error(f"Error handling event stream: {e}")
            time.sleep(1)

    logging.info("Docker event listener stopped.")

if __name__ == "__main__":
    main()