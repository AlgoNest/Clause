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
            raise Exception(f"GitHub Error: {r.status_code} - {r.text}")

        return r

    # ---------------------------
    def load_users(self) -> List[dict]:
        url = f"{self.base_url}/users/users.json"
        response = self._make_request("GET", url)

        if response is None:
            return []  # file not found

        content = base64.b64decode(response.json()["content"]).decode()
        return json.loads(content)

    # ---------------------------
    def save_users(self, users: List[dict]):
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
        users = self.load_users()
        users.append(user)
        self.save_users(users)

    # ---------------------------
    # Analysis saving system
    # ---------------------------
    def save_analysis(self, analysis_data: Dict[str, Any]) -> str:
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
        url = f"{self.base_url}/analyses/{analysis_id}.json"
        response = self._make_request("GET", url)
        content = base64.b64decode(response.json()["content"]).decode()
        return json.loads(content)

    # ---------------------------
    def list_analyses(self) -> List[str]:
        url = f"{self.base_url}/analyses"
        response = self._make_request("GET", url)
        if response is None:
            return []

        items = response.json()
        files = [i["name"].replace(".json", "") for i in items if i["type"] == "file"]
        return sorted(files, reverse=True)
