"""Workflow API invocation and polling tools.

Expected Workflow API response structures (Requirement 14.2):

1. Initial POST response (from call_workflow_api):
   {
       "task_id": "wf-abc123",
       "status": "processing"
   }

2. Poll response — in progress (from poll_workflow_status):
   {
       "task_id": "wf-abc123",
       "status": "processing"
   }

3. Poll response — completed with contract_name (triggers contract-specific post-processing):
   {
       "task_id": "wf-abc123",
       "status": "completed",
       "contract_name": "Acme Corp",
       "result": { ... }
   }

4. Poll response — completed without contract_name (triggers general post-processing):
   {
       "task_id": "wf-abc123",
       "status": "completed",
       "result": { ... }
   }
"""

import time

import requests
from strands.tools import tool


@tool
def call_workflow_api(
    transaction_id: str, sheet_data: dict, api_endpoint: str, api_key: str = None
) -> dict:
    """
    Submit sheet data to the workflow API.

    Sends a POST request to the API endpoint with the transaction ID and
    sheet data as a JSON payload. Includes an Authorization header when
    an API key is provided.

    Args:
        transaction_id: The transaction ID (e.g. 12345).
        sheet_data: Dictionary of sheet data to submit.
        api_endpoint: The workflow API endpoint URL.
        api_key: Optional API key for Authorization header.

    Returns:
        {"status": "success", "response": {...}}
        or {"status": "error", "error_type": "...", "message": "...", "status_code": int}
    """
    try:
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = api_key

        payload = {
            "transaction_id": transaction_id,
            "sheet_data": sheet_data,
        }

        response = requests.post(api_endpoint, json=payload, headers=headers)
        response.raise_for_status()

        # Expected initial response: {"task_id": "wf-abc123", "status": "processing"}
        return {"status": "success", "response": response.json()}
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response is not None else None
        body = ""
        try:
            body = e.response.text if e.response is not None else ""
        except Exception:
            pass
        return {
            "status": "error",
            "error_type": "HTTPError",
            "message": f"Workflow API returned HTTP {status_code}: {body}",
            "status_code": status_code,
        }
    except requests.exceptions.ConnectionError as e:
        return {
            "status": "error",
            "error_type": "ConnectionError",
            "message": f"Could not connect to workflow API at {api_endpoint}: {e}",
        }
    except Exception as e:
        return {
            "status": "error",
            "error_type": type(e).__name__,
            "message": f"Unexpected error calling workflow API: {e}",
        }


@tool
def poll_workflow_status(
    api_endpoint: str, task_id: str, api_key: str = None
) -> dict:
    """
    Poll the workflow API for completion with exponential backoff.

    Makes GET requests to {api_endpoint}/status/{task_id}, waiting
    2^n seconds between attempt n (1-10). Stops when the response
    status is "completed" or after 10 attempts.

    Args:
        api_endpoint: The workflow API base endpoint URL.
        task_id: The task ID returned by the initial API call.
        api_key: Optional API key for Authorization header.

    Returns:
        {"status": "completed", "response": {...}}
        or {"status": "timeout", "last_status": "...", "attempts": int}
        or {"status": "error", "error_type": "...", "message": "..."}
    """
    max_attempts = 10
    last_status = None

    try:
        headers = {}
        if api_key:
            headers["Authorization"] = api_key

        for attempt in range(1, max_attempts + 1):
            delay = 2 ** attempt
            time.sleep(delay)

            response = requests.get(
                f"{api_endpoint}/status/{task_id}", headers=headers
            )
            response.raise_for_status()

            data = response.json()
            last_status = data.get("status", "unknown")

            if last_status == "completed":
                # Completed response may include "contract_name" for contract-specific
                # post-processing, or omit it for general post-processing.
                # See module docstring for full response structure examples.
                return {"status": "completed", "response": data}

        return {
            "status": "timeout",
            "last_status": last_status,
            "attempts": max_attempts,
        }
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response is not None else None
        body = ""
        try:
            body = e.response.text if e.response is not None else ""
        except Exception:
            pass
        return {
            "status": "error",
            "error_type": "HTTPError",
            "message": f"Polling API returned HTTP {status_code}: {body}",
        }
    except requests.exceptions.ConnectionError as e:
        return {
            "status": "error",
            "error_type": "ConnectionError",
            "message": f"Could not connect to workflow API at {api_endpoint}: {e}",
        }
    except Exception as e:
        return {
            "status": "error",
            "error_type": type(e).__name__,
            "message": f"Unexpected error polling workflow status: {e}",
        }
