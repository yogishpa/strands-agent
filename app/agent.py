"""Agent definition for the Contract Workflow Agent."""

from strands import Agent
from strands.models.bedrock import BedrockModel

try:
    from tools.parse_tools import parse_input, lookup_transaction_id
    from tools.s3_tools import download_s3_file
    from tools.excel_tools import read_excel_sheets
    from tools.api_tools import call_workflow_api, poll_workflow_status
    from tools.postprocess_tools import run_post_processing
except ImportError:
    from app.tools.parse_tools import parse_input, lookup_transaction_id
    from app.tools.s3_tools import download_s3_file
    from app.tools.excel_tools import read_excel_sheets
    from app.tools.api_tools import call_workflow_api, poll_workflow_status
    from app.tools.postprocess_tools import run_post_processing

SYSTEM_PROMPT = """You are a Contract Workflow Agent that automates contract and transaction processing.
You have access to the following tools and should use them in this sequence:

1. **parse_input** — Parse the user's natural language message. If the user provides a transaction ID (any format), extract it and pass it as the `transaction_id` parameter. Otherwise, the tool will check for known contract names.
2. **lookup_transaction_id** — If a Contract_Name was found (not a Transaction_ID), look up the corresponding Transaction_ID from the contract mapping.
3. **download_s3_file** — Download the Excel file from S3 using the Transaction_ID. The S3 path is {{s3_prefix}}/process_{{transaction_id}}.xlsx in bucket {{s3_bucket}}. Use aws_region={{aws_region}}.
4. **read_excel_sheets** — Read all sheets from the downloaded Excel file.
5. **call_workflow_api** — Submit the sheet data to the workflow API at {{api_endpoint}} along with the transaction_id.
6. **poll_workflow_status** — Poll the workflow API for completion using the task_id from the previous response.
7. **run_post_processing** — Run post-processing on the completed workflow response.

Configuration values for tool parameters:
- s3_bucket: {{s3_bucket}}
- s3_prefix: {{s3_prefix}}
- api_endpoint: {{api_endpoint}}
- aws_region: {{aws_region}}

Always pass these configuration values to the tools that require them. If a tool returns an error, relay the error message to the user clearly and suggest corrective actions. Do not proceed to the next step if the current step fails.

When reporting progress, be concise and informative. After the full workflow completes, provide a summary of what was processed and the final result.
"""


class ToolTrackingCallbackHandler:
    """Callback handler that captures tool calls into a shared log AND prints to console."""

    def __init__(self, tool_log: list):
        self.tool_log = tool_log
        self.tool_count = 0
        self.previous_tool_use = None
        self.current_text = []

    def __call__(self, **kwargs):
        data = kwargs.get("data", "")
        complete = kwargs.get("complete", False)
        current_tool_use = kwargs.get("current_tool_use", {})
        reasoning_text = kwargs.get("reasoningText", "")

        # Console: print reasoning text
        if reasoning_text:
            print(reasoning_text, end="")
            self.current_text.append(reasoning_text)

        # Console: print streamed text
        if data:
            print(data, end="" if not complete else "\n")
            self.current_text.append(data)

        # Capture tool calls
        if current_tool_use and current_tool_use.get("name"):
            if self.previous_tool_use != current_tool_use:
                # Flush accumulated text as a "thinking" entry
                if self.current_text:
                    text = "".join(self.current_text).strip()
                    if text:
                        self.tool_log.append({"type": "thinking", "text": text})
                    self.current_text = []

                self.previous_tool_use = current_tool_use
                self.tool_count += 1
                tool_name = current_tool_use.get("name", "unknown")

                # Console: print tool call
                print(f"\nTool #{self.tool_count}: {tool_name}")

                self.tool_log.append({
                    "type": "tool_call",
                    "name": tool_name,
                    "input": current_tool_use.get("input", {}),
                    "tool_number": self.tool_count,
                })

        # On complete, flush remaining text
        if complete:
            if self.current_text:
                text = "".join(self.current_text).strip()
                if text:
                    self.tool_log.append({"type": "thinking", "text": text})
                self.current_text = []
            if data:
                print("\n")


def create_agent(config: dict, tool_log: list = None) -> Agent:
    """
    Create a Strands Agent with all tools registered.

    Args:
        config: dict with keys 's3_bucket', 's3_prefix', 'api_endpoint', 'aws_region'
        tool_log: optional list to append tool call events to (for UI display)

    Returns:
        Configured Strands Agent instance
    """
    model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
        region_name=config.get("aws_region", "us-east-1"),
    )

    system_prompt = SYSTEM_PROMPT.replace("{{s3_bucket}}", config.get("s3_bucket", ""))
    system_prompt = system_prompt.replace("{{s3_prefix}}", config.get("s3_prefix", ""))
    system_prompt = system_prompt.replace("{{api_endpoint}}", config.get("api_endpoint", ""))
    system_prompt = system_prompt.replace("{{aws_region}}", config.get("aws_region", "us-east-1"))

    # Use custom callback handler if tool_log provided, otherwise suppress output
    callback = ToolTrackingCallbackHandler(tool_log) if tool_log is not None else None

    agent = Agent(
        model=model,
        system_prompt=system_prompt,
        tools=[
            parse_input,
            lookup_transaction_id,
            download_s3_file,
            read_excel_sheets,
            call_workflow_api,
            poll_workflow_status,
            run_post_processing,
        ],
        callback_handler=callback,
    )

    return agent
