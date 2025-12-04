import json
import os
import requests
from datetime import datetime
from typing import Dict, Any, List, Optional
import base64

class GitHubService:
    def __init__(self, token: str, repo_owner: str, repo_name: str):
        """
        Initialize GitHub service with authentication and repository details.
        """
        self.token = token  # Use the passed token (from ENV variable)
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github+json"
        }

    # ---------------------------
    # Make HTTP request
    # ---------------------------
    def _make_request(self, method: str, url: str, data: Optional[dict] = None) -> requests.Response:
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=self.headers, timeout=30)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=self.headers, json=data, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            if response.status_code == 403 and 'rate limit' in response.text.lower():
                raise Exception("GitHub API rate limit exceeded. Try later.")
            elif response.status_code == 404:
                return None
            elif not response.ok:
                raise Exception(f"GitHub API error: {response.status_code} - {response.text}")

            return response
        except requests.exceptions.Timeout:
            raise Exception("Request timed out.")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error: {str(e)}")

    # ---------------------------
    # Load all users
    # ---------------------------
    def load_users(self) -> List[dict]:
        file_path = "users/users.json"  # Root level file
        url = f"{self.base_url}/contents/{file_path}"

        response = self._make_request("GET", url)
        if response is None:
            return []  # File does not exist yet

        content = response.json().get("content", "")
        if not content:
            return []

        decoded = base64.b64decode(content).decode()
        try:
            users = json.loads(decoded)
            if isinstance(users, list):
                return users
            return []
        except:
            return []

    # ---------------------------
    # Save users list
    # ---------------------------
    def save_users(self, users: List[dict]):
        file_path = "users/users.json"
        url = f"{self.base_url}/contents/{file_path}"

        # Check for existing SHA
        sha = None
        response = self._make_request("GET", url)
        if response is not None:
            sha = response.json().get("sha")

        content = json.dumps(users, indent=2)
        encoded = base64.b64encode(content.encode()).decode()

        data = {
            "message": "Update users.json",
            "content": encoded
        }
        if sha:
            data["sha"] = sha

        self._make_request("PUT", url, data)

    # ---------------------------
    # Add single user
    # ---------------------------
    def add_user(self, user: dict):
        users = self.load_users()
        users.append(user)
        self.save_users(users)

    # ---------------------------
    # Save analysis data
    # ---------------------------
    def save_analysis(self, analysis_data: Dict[str, Any]) -> str:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        file_path = f"contracts/{timestamp}/analysis.json"
        url = f"{self.base_url}/contents/{file_path}"

        content = json.dumps(analysis_data, indent=2)
        encoded = base64.b64encode(content.encode()).decode()

        data = {
            "message": f"Add analysis {timestamp}",
            "content": encoded
        }

        # Check SHA
        response = self._make_request("GET", url)
        if response is not None:
            data["sha"] = response.json().get("sha")

        self._make_request("PUT", url, data)
        return timestamp

    # ---------------------------
    # Get analysis data
    # ---------------------------
    def get_analysis(self, analysis_id: str) -> Dict[str, Any]:
        file_path = f"contracts/{analysis_id}/analysis.json"
        url = f"{self.base_url}/contents/{file_path}"

        response = self._make_request("GET", url)
        content = response.json()["content"]
        decoded = base64.b64decode(content).decode()
        return json.loads(decoded)

    # ---------------------------
    # List all analyses
    # ---------------------------
    def list_analyses(self) -> List[str]:
        url = f"{self.base_url}/contents/contracts"
        response = self._make_request("GET", url)
        if response is None:
            return []

        items = response.json()
        dirs = [i["name"] for i in items if i["type"] == "dir"]
        return sorted(dirs, reverse=True)
