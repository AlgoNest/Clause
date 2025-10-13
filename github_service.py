import json
import os
import requests
from datetime import datetime
from typing import Dict, Any, List, Optional

class GitHubService:
    def __init__(self, token: str, repo_owner: str, repo_name: str):
        """
        Initialize GitHub service with authentication and repository details.

        Args:
            token (str): GitHub personal access token.
            repo_owner (str): Owner of the GitHub repository.
            repo_name (str): Name of the GitHub repository.
        """
        self.token = token
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }

    def _make_request(self, method: str, url: str, data: Optional[Dict] = None) -> requests.Response:
        """
        Make a request to GitHub API with error handling.

        Args:
            method (str): HTTP method (GET, PUT, etc.).
            url (str): API endpoint URL.
            data (Optional[Dict]): JSON data for POST/PUT requests.

        Returns:
            requests.Response: The response object.

        Raises:
            Exception: For network errors, rate limits, etc.
        """
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=self.headers, timeout=30)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=self.headers, json=data, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            if response.status_code == 403 and 'rate limit' in response.text.lower():
                raise Exception("GitHub API rate limit exceeded. Please try again later.")
            elif response.status_code == 404:
                raise Exception("Repository or file not found.")
            elif not response.ok:
                raise Exception(f"GitHub API error: {response.status_code} - {response.text}")

            return response

        except requests.exceptions.Timeout:
            raise Exception("Request timed out. Check your network connection.")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error: {str(e)}")

    def save_analysis(self, analysis_data: Dict[str, Any]) -> str:
        """
        Save analysis data to GitHub repository as a JSON file.

        Args:
            analysis_data (Dict[str, Any]): The analysis data to save.

        Returns:
            str: The analysis ID (timestamp-based).
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        analysis_id = timestamp
        file_path = f"contracts/{timestamp}/analysis.json"

        # Create the directory structure implicitly by creating the file
        url = f"{self.base_url}/contents/{file_path}"

        # Check if file exists to get SHA for update
        sha = None
        try:
            existing_response = self._make_request("GET", url)
            sha = existing_response.json().get("sha")
        except Exception:
            # File doesn't exist, which is fine for creation
            pass

        # Prepare the content
        content = json.dumps(analysis_data, indent=2)
        import base64
        encoded_content = base64.b64encode(content.encode()).decode()

        data = {
            "message": f"Add analysis for {analysis_id}",
            "content": encoded_content
        }
        if sha:
            data["sha"] = sha

        self._make_request("PUT", url, data)
        return analysis_id

    def get_analysis(self, analysis_id: str) -> Dict[str, Any]:
        """
        Retrieve a specific analysis by ID.

        Args:
            analysis_id (str): The analysis ID (timestamp).

        Returns:
            Dict[str, Any]: The analysis data.
        """
        file_path = f"contracts/{analysis_id}/analysis.json"
        url = f"{self.base_url}/contents/{file_path}"

        response = self._make_request("GET", url)
        content = response.json()["content"]
        import base64
        decoded_content = base64.b64decode(content).decode()
        return json.loads(decoded_content)

    def list_analyses(self) -> List[str]:
        """
        List all analysis IDs (timestamps) in the repository.

        Returns:
            List[str]: List of analysis IDs.
        """
        url = f"{self.base_url}/contents/contracts"
        try:
            response = self._make_request("GET", url)
            items = response.json()
            analysis_ids = []
            for item in items:
                if item["type"] == "dir":
                    analysis_ids.append(item["name"])
            return sorted(analysis_ids, reverse=True)  # Most recent first
        except Exception as e:
            if "404" in str(e):
                return []  # No contracts directory yet
            raise

    def list_analyses_with_data(self) -> List[Dict[str, Any]]:
        """
        List all analyses with their full data for dashboard display.

        Returns:
            List[Dict[str, Any]]: List of analysis data dictionaries.
        """
        analysis_ids = self.list_analyses()
        analyses = []

        for analysis_id in analysis_ids:
            try:
                analysis_data = self.get_analysis(analysis_id)
                # Add the ID to the data for reference
                analysis_data['analysis_id'] = analysis_id
                analyses.append(analysis_data)
            except Exception as e:
                # Skip analyses that can't be loaded
                print(f"Warning: Could not load analysis {analysis_id}: {e}")
                continue

        return analyses

# Example usage:
# service = GitHubService(token="your_token", repo_owner="your_owner", repo_name="your_repo")
# analysis_id = service.save_analysis({"clause_type": "Limitation of Liability", ...})
# analysis = service.get_analysis(analysis_id)
# analyses = service.list_analyses()
