import logging
import os
import requests
import time
from datetime import datetime, timezone
from ntfy_integration import NtfyIntegration as ntfy

class NpmIntegration:
    _token_cache = {
        "token": None,
        "expiry_time": 0  # UNIX timestamp when token expires
    }

    @staticmethod
    def get_npm_token() -> str:
        """
        Retreives and caches the NPM Bearer Token.
        Caches the token until shortly before expiry (e.g., 5 seconds before).
        """
        now = time.time()
        if (NpmIntegration._token_cache["token"] is not None and now < NpmIntegration._token_cache["expiry_time"] - 5):
            return NpmIntegration._token_cache["token"]

        npm_base_url = os.getenv('NPM_SERVER_URL')
        if not npm_base_url:
            logging.error("NPM_SERVER_URL not set in environment")
            return None
        
        npm_api_url = f"{npm_base_url}/api/tokens"
        payload = {
            "identity": os.getenv('NPM_USER'),
            "secret": os.getenv('NPM_SECRET'),
        }

        try:
            response = requests.post(npm_api_url, json=payload, timeout=10)
            response.raise_for_status()
            token_data = response.json()
            token = token_data.get("token")
            expires_str = token_data.get("expires")  # example: "2025-04-27T22:48:02.000Z"

            if not token or not expires_str:
                logging.error("No token found in NPM token response")
                return None
            
            expires_dt = datetime.strptime(expires_str, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
            expiry_unix = expires_dt.timestamp()
            
            NpmIntegration._token_cache["token"] = token
            NpmIntegration._token_cache["expiry_time"] = expiry_unix

            logging.info("NPM Bearer Token acquired and cached")
            if os.getenv('USE_NTFY_FOR_UPDATES').lower() == "true":
                ntfy.ntfy_post("New Bearer Token acquired!", "Token POST succeeded", "white_check_mark")
            return token
        
        except requests.RequestException as e:
            err_msg = f"Error getting NPM Bearer Token: {e}"
            logging.error(err_msg)
            if os.getenv('USE_NTFY_FOR_UPDATES').lower() == "true":
                ntfy.ntfy_post(err_msg, "Token POST failed...", "warning", "high")
            return None

    @staticmethod
    def get_cert_id(domain:str) -> int:
        """
        Retrieves the certificate ID for a given domain from NPM.
        Returns the certificate ID if found, otherwise returns None.
        """
        npm_base_url = os.getenv('NPM_SERVER_URL')
        if not npm_base_url:
            logging.error("NPM_SERVER_URL not set in environment")
            return None
        
        npm_api_key = NpmIntegration.get_npm_token()
        if not npm_api_key:
            logging.error("Failed to retrieve NPM Bearer Token")
            return None

        npm_api_url = f"{npm_base_url}/api/nginx/certificates"
        headers = {
            "Authorization": f"Bearer {npm_api_key}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.get(npm_api_url, headers=headers, timeout=10)
            response.raise_for_status()
            certs_data = response.json()

            for cert in certs_data:
                if domain in cert.get("domain_names", []):
                    return cert.get("id")

            logging.warning(f"No certificate found for domain: {domain}")
            return None
        
        except requests.RequestException as e:
            err_msg = f"Error getting certificate ID for domain {domain}: {e}"
            logging.error(err_msg)
            if os.getenv('USE_NTFY_FOR_UPDATES').lower() == "true":
                ntfy.ntfy_post(err_msg, "Certificate ID GET failed...", "warning", "high")
            return None

    @staticmethod
    def create_npm_proxy_host(host: str, port: int, cert_id: int) -> bool:
        """
        Creates new proxy host in NPM based on host, port of a new container and certificate ID.
        Returns True on success, False on failure.
        """
        npm_base_url = os.getenv('NPM_SERVER_URL')
        if not npm_base_url:
            logging.error("NPM_SERVER_URL not set in environment")
            return False
        npm_api_key = NpmIntegration.get_npm_token()
        # npm_api_key = "place your key here if you want to use a static one"

        npm_api_url = f"{npm_base_url}/api/nginx/proxy-hosts"
        headers = {
            "Authorization": f"Bearer {npm_api_key}"
        }
        payload = {
            "domain_names": [host],
            "forward_host": os.getenv('HOST_IP_ADDRESS'),
            "forward_port": port,
            "access_list_id": 0,
            "certificate_id": cert_id,
            "ssl_forced": 1,
            "caching_enabled": 0,
            "block_exploits": 1,
            "advanced_config": "",
            "meta": {
                "letsencrypt_agree": 1,
                "dns_challenge": 1
            },
            "allow_websocket_upgrade": 1,
            "http2_support": 1,
            "forward_scheme": "http",
            "enabled": 1,
            "locations": [],
            "hsts_enabled": 0,
            "hsts_subdomains": 0
        }

        try:
            response = requests.post(npm_api_url, headers=headers, json=payload, timeout=10)
            if response.status_code == 201:
                logging.info(f"New proxy host created: {host}")
                if(os.getenv('USE_NTFY_FOR_UPDATES').upper() == "TRUE"):
                    ntfy.ntfy_post(f"{host} proxy host created!", "New proxy POST succeeded", "white_check_mark")
                return True
            else:
                try:
                    error_json = response.json()
                except ValueError:
                    error_json = {}
                
                error_msg = error_json.get("message", "") or response.text or ""
                
                if "already in use" in error_msg.lower():
                    msg = f"Proxy host for '{host}' already exists. Skipping creation."
                    logging.info(msg)
                    if os.getenv('USE_NTFY_FOR_UPDATES', '').lower() == "true":
                        ntfy.ntfy_post(msg, "Proxy exists", "information")
                    return True  # Return True to indicate "successful" handling/skipping

                # Other errors
                err_msg = (f"Failed to create proxy host {host}. Status: {response.status_code}, Response: {response.text}")
                logging.error(err_msg)
                if os.getenv('USE_NTFY_FOR_UPDATES', '').lower() == "true":
                    ntfy.ntfy_post(err_msg, "New proxy POST failed...", "warning", "high")
                return False
        
        except requests.RequestException as e:
            err_msg = f"Exception creating proxy host {host}: {e}"
            logging.error(err_msg)
            if os.getenv('USE_NTFY_FOR_UPDATES', '').lower() == "true":
                ntfy.ntfy_post(err_msg, "New proxy POST failed...", "warning", "high")
            return False