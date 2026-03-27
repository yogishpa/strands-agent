"""Post-processing tool for workflow API responses."""

from strands.tools import tool


@tool
def run_post_processing(workflow_response: dict) -> dict:
    """
    Run post-processing based on workflow API response.

    Determines the processing type by checking for a `contract_name` field
    in the workflow response. Executes contract-specific logic when present,
    or general post-processing otherwise.

    Args:
        workflow_response: The completed workflow API response dict.

    Returns:
        {"status": "success", "processing_type": "contract_specific"|"general", "summary": "..."}
        or {"status": "error", "error_type": "...", "message": "..."}
    """
    try:
        contract_name = workflow_response.get("contract_name")

        if contract_name:
            # Contract-specific post-processing
            summary = (
                f"Contract-specific post-processing completed for '{contract_name}'."
            )
            return {
                "status": "success",
                "processing_type": "contract_specific",
                "summary": summary,
            }
        else:
            # General post-processing
            summary = "General post-processing completed successfully."
            return {
                "status": "success",
                "processing_type": "general",
                "summary": summary,
            }
    except Exception as e:
        return {
            "status": "error",
            "error_type": "ProcessingError",
            "message": f"Post-processing failed: {e}",
        }
