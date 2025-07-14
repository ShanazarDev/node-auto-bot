import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()


class NodeSetup:
    """
    Class for managing Marzban nodes
    """

    def __init__(self, username: str, password: str, url: str) -> None:
        self.username = username
        self.password = password
        self.main_url = url
        self.auth_url = f"{self.main_url}/api/admin/token"
        self.node_url = f"{self.main_url}/api/node"
        self.nodes_url = f"{self.main_url}/api/nodes"
        self.token = ""

    def _auth(self) -> None:
        auth_data = {"username": self.username, "password": self.password}

        auth = requests.post(
            self.auth_url,
            data=auth_data,
            timeout=10,
        )
        if auth.status_code == 200:
            self.token = auth.json()["access_token"]
        else:
            raise Exception(f"Authentication failed: {auth.text}")

    def get_nodes(self) -> dict:
        nodes = requests.get(
            self.nodes_url,
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=10,
        )

        if nodes.status_code == 200:
            return nodes.json()
        elif nodes.status_code == 401:
            self._auth()
            return self.get_nodes()
        else:
            raise Exception(f"Nodes retrieval failed: {nodes.text}")

    def create_node(
        self, name: str, address: str, port: int, api_port: int, new_host: bool
    ) -> dict:
        node_data = {
            "add_as_new_host": "true" if new_host else "false",
            "address": address,
            "api_port": api_port,
            "name": name,
            "port": port,
            "usage_coefficient": 1,
        }
        node = requests.post(
            self.node_url,
            headers={"Authorization": f"Bearer {self.token}"},
            data=json.dumps(node_data),
            timeout=10,
        )
        if node.status_code == 200:
            return node.json()
        elif node.status_code == 401:
            self._auth()
            return self.create_node(name, address, port, api_port, new_host)
        else:
            raise Exception(f"Node creation failed: {node.text}")

    def delete_node(self, node_id: str) -> dict:
        node = requests.delete(
            f"{self.node_url}/{node_id}",
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=10,
        )
        if node.status_code == 200:
            return node.json()
        elif node.status_code == 401:
            self._auth()
            return self.delete_node(node_id)
        else:
            raise Exception(f"Node deletion failed: {node.text}")


if __name__ == "__main__":
    node = NodeSetup(
        os.getenv("MARZBAN_USERNAME"),
        os.getenv("MARZBAN_PASSWORD"),
        os.getenv("MARZBAN_URL"),
    )
    print(node.get_nodes())
