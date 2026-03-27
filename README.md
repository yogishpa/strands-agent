# Contract Workflow Agent

A Streamlit-based conversational agent that automates contract and transaction workflow processing using the [Strands Agents SDK](https://github.com/strands-agents/sdk-python) with Amazon Bedrock (Claude Sonnet 4).

## Overview

Users interact via a chat UI, describing their request in natural language. The agent orchestrates a multi-step pipeline:

1. Parse user input to extract a transaction ID or contract name
2. Look up contract names to resolve transaction IDs
3. Download the corresponding Excel file from S3
4. Read all sheets from the Excel file
5. Submit the sheet data (as JSON) to a workflow REST API
6. Poll the API for completion
7. Run post-processing on the result

The agent streams its reasoning and tool calls to the UI in real time.

## Project Structure

```
├── app/
│   ├── __init__.py
│   ├── app.py                  # Streamlit entry point
│   ├── agent.py                # Strands Agent definition + callback handler
│   └── tools/
│       ├── __init__.py
│       ├── parse_tools.py      # Input parsing & contract lookup
│       ├── s3_tools.py         # S3 file download
│       ├── excel_tools.py      # Excel sheet reading (openpyxl)
│       ├── api_tools.py        # Workflow API call & polling
│       └── postprocess_tools.py # Post-processing logic
├── tests/                      # Property-based tests (hypothesis)
├── contract_mapping.json       # Contract name → transaction ID mapping
├── requirements.txt
├── .env.example
└── README.md
```

## Prerequisites

- Python 3.10+
- AWS credentials configured (for Bedrock and S3 access)
- Access to Amazon Bedrock with Claude Sonnet 4 enabled

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Configure environment variables (copy and edit):

```bash
cp .env.example .env
```

Required variables:
| Variable | Description |
|---|---|
| `AWS_REGION` | AWS region for Bedrock and S3 (e.g. `us-east-1`) |
| `S3_BUCKET` | S3 bucket containing transaction Excel files |
| `S3_PREFIX` | S3 key prefix (folder path), leave empty if files are at bucket root |
| `API_ENDPOINT` | Workflow REST API endpoint URL |
| `API_KEY` | Optional API key for the workflow API |

3. Update `contract_mapping.json` with your contract name → transaction ID mappings.

## Running the App

```bash
streamlit run app/app.py
```

The app will be available at http://localhost:8501.

### Sidebar Configuration

The sidebar lets you override S3 bucket, S3 prefix, API endpoint, and AWS region at runtime. Values are pre-populated from environment variables.

### Example Prompts

- "Process transaction 12345"
- "Can you perform the CMR for transaction 67890"
- "Process Acme Corp contract"

## S3 File Naming Convention

The agent constructs the S3 file path as:

```
s3://{bucket}/{prefix}/process_{transaction_id}.xlsx
```

If the prefix is empty, it looks for `process_{transaction_id}.xlsx` at the bucket root.

## Running Tests

The test suite uses [hypothesis](https://hypothesis.readthedocs.io/) for property-based testing:

```bash
pytest tests/ -v
```

## Architecture

The agent uses a tool-based architecture where each workflow step is an independent `@tool`-decorated function. The Strands SDK agent (backed by Claude Sonnet 4 via Bedrock) decides which tools to call and in what order based on the user's natural language input.

All tools return a consistent structured response:

```python
# Success
{"status": "success", ...tool-specific fields...}

# Error
{"status": "error", "error_type": "...", "message": "..."}
```

## Sensitive Data Notice

- No credentials, API keys, or account IDs are hardcoded in the source code
- All secrets are managed via environment variables
- The `contract_mapping.json` ships with fictional sample data (Acme Corp, Globex Industries, Initech Solutions)
- The `.env.example` contains only placeholder values
