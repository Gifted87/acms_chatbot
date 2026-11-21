import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# CONFIGURATION
# ==============================================================================
ACMS_BASE_URL = os.getenv("ACMS_BASE_URL", "http://localhost:4000/api/v1").rstrip("/")
CMS_URL = os.getenv("ACMS_INGEST_URL", f"{ACMS_BASE_URL}/ingest")
HEADERS = {
    "Content-Type": "application/json",
    "x-agent-id": "root" 
}
INPUT_FILE = "cuad_data.json"

# supported extensions when ingesting folders
SUPPORTED_EXTS = {".txt", ".md", ".json", ".csv"}  # treat others as plain text

def ingest_contract_node(contract_data):
    """
    Ingests one contract as one single ACMS node.
    The fact_text is a concatenation of Title and Context to ensure 
    the embedding reflects the total content of the node.
    """
    title = contract_data.get("title", "Untitled Contract")
    full_text = contract_data.get("context", "")
    
    # Combined Head for embedding: Title + Content
    combined_head = f"CONTRACT: {title}\n\nCONTENT: {full_text}"

    payload = {
        "agent_id": "root",
        "fact_text": combined_head, # This is used for the embedding
        "acls": {"read": ["public"], "write": ["root"]},
        "provenance": {
            "source": "CUAD_Dataset",
            "doc_title": title
        },
        "description_payloads": [
            {
                "type": "object",
                "object_type": "generic",
                "data": contract_data # The entire JSON blob as the Body
            }
        ]
    }

    try:
        # Note: Large combined heads take longer to embed. Timeout set to 120s.
        response = requests.post(CMS_URL, json=payload, headers=HEADERS, timeout=120)
        if response.status_code in [200, 201, 202]:
            print(f"✅ Ingested: {title} (Combined Head & Body)")
        else:
            print(f"❌ Failed {title}: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Connection Error during {title}: {e}")

def ingest_folder(folder_path):
    """Walks through every file in the folder (non-recursive) and creates an
    ACMS node for each file. The node title is the file name and the content
    is the file's textual contents. Binary files are skipped.
    """
    files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
    print(f"📁 Found {len(files)} files in {folder_path}, ingesting...")

    for fname in files:
        ext = os.path.splitext(fname)[1].lower()
        if SUPPORTED_EXTS and ext not in SUPPORTED_EXTS:
            print(f"⚠️  Skipping unsupported file type: {fname}")
            continue
        path = os.path.join(folder_path, fname)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"❌ Could not read {fname}: {e}")
            continue
        contract_data = {"title": fname, "context": content}
        ingest_contract_node(contract_data)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Ingest JSON dataset or directory of files into ACMS.")
    parser.add_argument("--input", "-i", default=INPUT_FILE,
                        help="Path to JSON file (default cuad_data.json) or folder to ingest.")
    args = parser.parse_args()

    if os.path.isdir(args.input):
        ingest_folder(args.input)
    else:
        if not os.path.exists(args.input):
            print(f"❌ File not found: {args.input}")
            return
        with open(args.input, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        contracts = raw_data.get("data", [])
        print(f"🚀 Ingesting {len(contracts)} atomic contract nodes...")

        for contract in contracts:
            ingest_contract_node(contract)

if __name__ == "__main__":
    main()
