# ACMS Legal Analyst

ACMS Legal Analyst is a Streamlit prototype for exploring contract information stored in an ACMS neural memory service. It retrieves relevant nodes for a question, sends the retrieved context to Google Gemini for a cited response, and displays the retrieved evidence alongside the conversation.

This is an experimental research tool. It is not a lawyer, does not provide legal advice, and should not be used to make legal or business decisions without review by a qualified professional.

## Features

- Ask natural language questions about contract clauses, governing law, liability, and dates.
- Retrieve up to 15 relevant ACMS nodes and display source content in an evidence panel.
- Generate responses with Gemini 2.5 Flash Lite and request citations to retrieved source IDs.
- Ingest a JSON contract dataset or supported text files into ACMS with the included command line utility.

## Architecture

The application uses three components:

1. `app.py` provides the Streamlit chat interface and sends questions to ACMS.
2. `acms_client.py` calls the ACMS health, query, and ingestion endpoints at `http://localhost:4000/api/v1`.
3. Google Gemini generates an answer from the retrieved ACMS context. The Gemini API key is entered in the app sidebar.

Questions and retrieved contract text are sent to the configured ACMS service. Retrieved contract text and the question are also sent to Google Gemini for answer generation. Use only data you are authorized to process, and review the providers' data handling terms before using sensitive documents.

## Requirements

- Python 3.10 or later
- A running ACMS service with its API available at `http://localhost:4000/api/v1`
- A Google Gemini API key

## Setup

```bash
git clone https://github.com/Gifted87/acms_chatbot.git
cd acms_chatbot
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

On Windows PowerShell, activate the virtual environment with:

```powershell
.venv\Scripts\Activate.ps1
```

Open the local Streamlit URL shown in the terminal, enter a Gemini API key in the sidebar, and ask a question. Confirm that ACMS is running before starting the app; its health status is shown in the sidebar.

## Ingest documents

`acms_ingest.py` accepts either a JSON dataset containing a top-level `data` array or a directory of `.txt`, `.md`, `.json`, and `.csv` files. It posts the documents to the ACMS ingest API.

```bash
python acms_ingest.py --input path/to/contracts.json
python acms_ingest.py --input path/to/text-documents/
```

The ingestion utility sends document contents to ACMS. Check that the configured service and its access controls are suitable before uploading real contracts. The default input filename in the script is `cuad_data.json`; that dataset is not included in this repository.

## Project files

| File | Purpose |
| --- | --- |
| `app.py` | Streamlit chat UI, ACMS retrieval, evidence display, and Gemini responses |
| `acms_client.py` | ACMS health, query, and ingest requests |
| `acms_ingest.py` | Dataset and directory ingestion utility |
| `requirements.txt` | Python dependencies |

## Limitations and security

- This is a prototype. Citations point to retrieved nodes and do not establish that an answer is complete or legally correct.
- The app renders chat content using custom HTML. Do not expose it to untrusted users or networks without reviewing and hardening the rendering and access controls.
- The ACMS client defaults to a local, unauthenticated HTTP endpoint. Keep the service on a trusted network and add appropriate authentication and transport security before deployment.
- The Gemini key is entered in the browser UI and passed to the Google Generative AI client for the session. Do not share the app with untrusted users.
- The `Clear Memory` control clears the current browser session's chat and evidence state; it does not delete records from ACMS.

## License

No license file is currently included. All rights are reserved unless the project owner adds a license granting reuse permissions.
