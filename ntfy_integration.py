import logging
import os
import requests

class NtfyIntegration:
    @staticmethod
    def ntfy_post(message: str, title: str, tags: str, priority: str="default") -> bool:
        """
        Posts a message in NTFY chosen topic.
        Returns True if post succeeded, False otherwise.
        """
        ntfy_server_url = os.getenv('NTFY_SERVER_URL')
        ntfy_topic = os.getenv('NTFY_TOPIC')
        if not ntfy_server_url or not ntfy_topic:
            logging.error("NTFY_SERVER_URL or NTFY_TOPIC not set in environment")
            return False

        ntfy_base_url = f"{ntfy_server_url.rstrip('/')}/{ntfy_topic.strip('/')}"
        headers = {
            "Title": title,
            "Tags": tags,
            "Priority": priority
        }
        
        try:
            response = requests.post(ntfy_base_url, data=message, headers=headers, timeout=5)
            response.raise_for_status()
            logging.info(f"Sent NTFY notification: {title}")
            return True
        except requests.RequestException as e:
            logging.error(f"Failed to send NTFY notification: {e}")
            return False