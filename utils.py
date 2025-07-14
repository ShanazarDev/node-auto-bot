import os
import tempfile
from fabric import Connection
from typing import Dict, Any

import requests


class ServerManager:
    """Class for managing servers and configuring Marzban nodes"""

    def __init__(self, host: str, password: str):
        self.host = host
        self.password = password
        self.connection = None

    def connect(self) -> bool:
        """Connecting to the server"""
        try:
            connect_kwargs = {"password": self.password}
            self.connection = Connection(
                host=self.host, user="root", connect_kwargs=connect_kwargs
            )
            result = self.connection.run("echo 'Connection test'", hide=True)
            return not result.failed
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    def setup_marzban_node(self, service_port: int, api_port: int) -> Dict[str, Any]:
        """Setting up a Marzban node on the server"""
        if not self.connection:
            if not self.connect():
                return {"success": False, "error": "Failed to connect to server"}

        try:
            certificate = os.getenv("MARZBAN_NODE_CERT")
            if not certificate:
                return {
                    "success": False,
                    "error": "Certificate not found in environment",
                }

            script_content = self._generate_setup_script(
                certificate, service_port, api_port
            )

            with tempfile.NamedTemporaryFile(
                mode="w", delete=False, suffix=".sh"
            ) as temp_file:
                temp_file.write(script_content)
                temp_file.flush()
                temp_file_path = temp_file.name

            try:
                with self.connection.cd("/tmp"):
                    result = self.connection.run(
                        f"cat > setup_node.sh << 'SCRIPTEOF'\n{script_content}\nSCRIPTEOF",
                        hide=True,
                    )
                    if result.failed:
                        return {
                            "success": False,
                            "error": f"Failed to create script: {result.stderr}",
                        }

                    result = self.connection.run(
                        "sudo chmod 755 setup_node.sh", hide=True
                    )
                    if result.failed:
                        return {
                            "success": False,
                            "error": f"Failed to set permissions: {result.stderr}",
                        }

                    result = self.connection.run("sudo bash ./setup_node.sh", hide=True)
                    if result.failed:
                        return {
                            "success": False,
                            "error": f"Setup failed: {result.stderr}",
                        }

                    self.connection.run("sudo rm -f setup_node.sh", hide=True)

                    return {
                        "success": True,
                        "message": f"Node setup completed successfully! Available on port {service_port}",
                        "host": self.host,
                        "service_port": service_port,
                        "api_port": api_port,
                    }

            finally:
                os.unlink(temp_file_path)

        except Exception as e:
            return {"success": False, "error": f"Setup error: {str(e)}"}
        finally:
            if self.connection:
                self.connection.close()

    def _generate_setup_script(
        self, certificate: str, service_port: int, api_port: int
    ) -> str:
        """Generating a setup script"""
        return f"""#!/bin/bash
set -e

echo "=== Updating system..."
sudo apt update -y

echo "=== Installing dependencies..."
sudo apt install socat git curl -y

echo "=== Installing Docker..."
curl -fsSL https://get.docker.com | sh

echo "=== Cloning Marzban Node repository..."
git clone https://github.com/Gozargah/Marzban-node || (cd Marzban-node && git pull)
cd Marzban-node

echo "=== Creating certificate directory..."
sudo mkdir -p /var/lib/marzban-node

# Save certificate
cat > /tmp/cert.pem << 'CERTEOF'
{certificate}
CERTEOF

sudo mv /tmp/cert.pem /var/lib/marzban-node/ssl_client_cert.pem
sudo chmod 644 /var/lib/marzban-node/ssl_client_cert.pem

# Create docker-compose.yml
cat > docker-compose.yml << 'COMPOSEEOF'
version: '3'
services:
  marzban-node:
    image: gozargah/marzban-node:latest
    restart: always
    network_mode: host
    volumes:
      - /var/lib/marzban-node:/var/lib/marzban-node
    environment:
      SSL_CLIENT_CERT_FILE: "/var/lib/marzban-node/ssl_client_cert.pem"
      SERVICE_PROTOCOL: rest
      SERVICE_PORT: {service_port}
      XRAY_API_PORT: {api_port}
COMPOSEEOF

echo "=== Starting Marzban Node with Docker Compose..."
sudo docker compose up -d

echo "[SUCCESS] Node setup completed! Node should be available on port {service_port}"
"""

    def test_connection(self) -> bool:
        """Testing connection to the server"""
        try:
            result = self.connection.run("echo 'test'", hide=True)
            return not result.failed
        except:
            return False


def get_geo_ip(ip: str) -> str:
    """Getting geo-information by IP address"""
    response = requests.get(f"https://ipapi.co/{ip}/json")
    if response.status_code == 200:
        return f"{response.json()['city']} ({response.json()['country_name']})"
    elif response.status_code == 429:
        response = requests.get(f"https://ipinfo.io/{ip}/json")
        if response.status_code == 200:
            return f"{response.json()['city']} ({response.json()['country']})"
        else:
            return "Ghost"
    else:
        return "Ghost"
