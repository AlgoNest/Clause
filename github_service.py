import json
import base64
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional


class GitHubService:
    def __init__(self, token: str, repo_owner: str, repo_name: str):
        self.token = token
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents"
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github+json"
        }

    # ---------------------------
    def _make_request(self, method: str, url: str, data: Optional[dict] = None):
        if method == "GET":
            r = requests.get(url, headers=self.headers)
        elif method == "PUT":
            r = requests.put(url, headers=self.headers, json=data)
        else:
            raise ValueError("Invalid HTTP method")

        if r.status_code == 404:
            return None

        if not r.ok:
            raise Exception(f"GitHub Error {r.status_code}: {r.text}")

        return r

    # ---------------------------
    # USERS
    # ---------------------------
    def load_users(self) -> List[dict]:
        """
        Load users/users.json from GitHub.
        Returns [] if file does not exist.
        """
        url = f"{self.base_url}/users/users.json"
        response = self._make_request("GET", url)

        if response is None:
            return []

        content = response.json()["content"]
        decoded = base64.b64decode(content).decode()
        return json.loads(decoded)

    # ---------------------------
    def save_users(self, users: List[dict]):
        """
        Save full users list to GitHub.
        Automatically handles sha (required for update).
        """
        url = f"{self.base_url}/users/users.json"

        existing = self._make_request("GET", url)
        sha = existing.json().get("sha") if existing else None

        encoded = base64.b64encode(json.dumps(users, indent=2).encode()).decode()

        data = {
            "message": "Update users.json",
            "content": encoded
        }

        if sha:
            data["sha"] = sha

        self._make_request("PUT", url, data)

    # ---------------------------
    def add_user(self, user: dict):
        """
        Append a new user into users.json
        """
        users = self.load_users()
        users.append(user)
        self.save_users(users)

    # ---------------------------
    # ANALYSIS SYSTEM
    # ---------------------------
    def save_analysis(self, analysis_data: Dict[str, Any]) -> str:
        """
        Save a new analysis log in analyses/{timestamp}.json
        Always creates a NEW file so SHA is NOT needed.
        """
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
        file_path = f"analyses/{timestamp}.json"
        url = f"{self.base_url}/{file_path}"

        encoded = base64.b64encode(json.dumps(analysis_data, indent=2).encode()).decode()

        data = {
            "message": f"Add analysis {timestamp}",
            "content": encoded
        }

        self._make_request("PUT", url, data)
        return timestamp

    # ---------------------------
    def get_analysis(self, analysis_id: str) -> Dict[str, Any]:
        """
        Fetch a single analysis file
        """
        url = f"{self.base_url}/analyses/{analysis_id}.json"
        response = self._make_request("GET", url)

        if response is None:
            raise FileNotFoundError(f"Analysis {analysis_id} not found")

        content = base64.b64decode(response.json()["content"]).decode()
        return json.loads(content)

    # ---------------------------
    def list_analyses(self) -> List[str]:
        """
        Return all analysis file names WITHOUT .json extension
        """
        url = f"{self.base_url}/analyses"
        response = self._make_request("GET", url)

        if response is None:
            return []

        items = response.json()
        return sorted(
            [i["name"].replace(".json", "") for i in items if i["type"] == "file"],
            reverse=True
        )
