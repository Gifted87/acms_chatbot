import os
import requests
import json

class ACMSClient:
    def __init__(self, base_url=None):
        self.base_url = (base_url or os.getenv("ACMS_BASE_URL", "http://localhost:4000/api/v1")).rstrip("/")
        self.headers = {
            "Content-Type": "application/json",
            "x-agent-id": "gemini_bot"
        }

    def health_check(self):
        """Checks if the Elixir ACMS is running."""
        try:
            # We hit the health endpoint to see if the system is responsive
            res = requests.get(f"{self.base_url}/health/embedder", timeout=2)
            return res.status_code == 200
        except Exception:
            return False

    def query_memory(self, user_query):
        """
        Sends the user's question to ACMS.

        The backend may return two key pieces of information:
        * ``results`` - the list of relevant document nodes pulled from the
          neural memory.
        * ``unknown_unknowns`` - a separate list of insights or signals that
          the system thinks could be relevant but are not directly tied to any
          existing node. These "unknown unknowns" should be surfaced to the
          assistant so it can reason about them.

        Returns a tuple ``(results_list, unknowns_list)``. Either element may
        be empty if nothing was provided.
        """
        url = f"{self.base_url}/query"
        payload = {
            "query_text": user_query,
            "agent_id": "root",
            "max_results": 15,          # Retrieve top relevant nodes
            "min_relevance": 0.55,      # Filter out noise
            "reasoning_mode": "normal"
        }
        
        try:
            response = requests.post(url, headers=self.headers, data=json.dumps(payload))
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                unknowns = data.get("unknown_unknowns", [])
                return results, unknowns
            else:
                print(f"Query Error: {response.text}")
                return [], []
        except Exception as e:
            print(f"Connection Error: {e}")
            return [], []

    def ingest_memory(self, text, source_type="conversation"):
        """
        Saves the conversation back into ACMS so the bot remembers it forever.
        """
        url = f"{self.base_url}/ingest"
        
        payload = {
            "agent_id": "gemini_bot",
            "fact_text": text,
            "acls": {"read": ["root"], "write": ["system"]},
            "provenance": {
                "source": "chatbot_ui",
                "type": source_type
            },
            "description_payloads": [
                {"type": "text", "content": "Conversation Log"}
            ]
        }

        try:
            requests.post(url, headers=self.headers, data=json.dumps(payload))
        except Exception as e:
            print(f"Ingest Error: {e}")

    def upload_file(self, file_obj, filename):
        """
        Uploads a file to ACMS. The Elixir backend will shred, chunk, and embed it.
        """
        url = f"{self.base_url}/ingest/upload"
        
        try:
            files = {'file': (filename, file_obj, "multipart/form-data")}
            # Note: No custom headers here, requests handles multipart boundaries automatically
            response = requests.post(url, files=files)
            return response.status_code in [200, 201, 202]
        except Exception as e:
            print(f"Upload Error: {e}")
            return False
