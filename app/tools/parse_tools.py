"""Input parsing and contract lookup tools."""

import json
import os
import re

from strands.tools import tool


@tool
def parse_input(user_message: str, transaction_id: str = None) -> dict:
    """
    Parse user message to extract Transaction_ID or Contract_Name.

    The agent should extract the transaction_id from the user message and pass
    it directly. If transaction_id is provided, it is returned as-is. Otherwise,
    the tool checks for known contract names in the message.

    Args:
        user_message: The raw user message.
        transaction_id: Optional transaction ID already extracted by the agent.

    Returns:
        {"status": "success", "transaction_id": "..."}
        or {"status": "success", "contract_name": "..."}
        or {"status": "error", "message": "Could not determine transaction or contract"}
    """
    try:
        # If the agent already extracted a transaction ID, use it directly
        if transaction_id:
            return {"status": "success", "transaction_id": transaction_id}

        # Check for known contract names in the message
        mapping_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "contract_mapping.json",
        )
        with open(mapping_path, "r") as f:
            contract_mapping = json.load(f)

        message_lower = user_message.lower()
        for contract_name in contract_mapping:
            if contract_name.lower() in message_lower:
                return {"status": "success", "contract_name": contract_name}

        return {
            "status": "error",
            "error_type": "ParseError",
            "message": "Could not determine transaction or contract from the message.",
        }
    except Exception as e:
        return {
            "status": "error",
            "error_type": type(e).__name__,
            "message": str(e),
        }

@tool
def lookup_transaction_id(contract_name: str, mapping_file: str = "contract_mapping.json") -> dict:
    """
    Look up a Transaction_ID from a Contract_Name.

    Args:
        contract_name: The contract name to look up.
        mapping_file: Path to the contract mapping JSON file.

    Returns:
        {"status": "success", "transaction_id": "...", "contract_name": "..."}
        or {"status": "error", "message": "...", "available_contracts": [...]}
    """
    try:
        mapping_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            mapping_file,
        )
        with open(mapping_path, "r") as f:
            contract_mapping = json.load(f)

        # Case-insensitive lookup
        name_lower = contract_name.lower()
        for key, transaction_id in contract_mapping.items():
            if key.lower() == name_lower:
                return {
                    "status": "success",
                    "transaction_id": transaction_id,
                    "contract_name": key,
                }

        return {
            "status": "error",
            "error_type": "NotFoundError",
            "message": f"Contract name '{contract_name}' not found in mapping.",
            "available_contracts": list(contract_mapping.keys()),
        }
    except Exception as e:
        return {
            "status": "error",
            "error_type": type(e).__name__,
            "message": str(e),
        }

