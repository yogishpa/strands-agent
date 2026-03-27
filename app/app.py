"""Streamlit entry point for the Contract Workflow Agent."""

import json
import os

import streamlit as st

try:
    from agent import create_agent
except ImportError:
    from app.agent import create_agent

TOOL_LABELS = {
    "parse_input": "🔍 Parsing user input",
    "lookup_transaction_id": "📋 Looking up contract",
    "download_s3_file": "📥 Downloading from S3",
    "read_excel_sheets": "📊 Reading Excel sheets",
    "call_workflow_api": "🚀 Calling workflow API",
    "poll_workflow_status": "🔄 Polling API status",
    "run_post_processing": "⚙️ Running post-processing",
}


def build_sidebar_config() -> dict:
    with st.sidebar:
        st.header("Configuration")
        s3_bucket = st.text_input("S3 Bucket", value=os.environ.get("S3_BUCKET", ""))
        s3_prefix = st.text_input("S3 Prefix", value=os.environ.get("S3_PREFIX", ""))
        api_endpoint = st.text_input("API Endpoint", value=os.environ.get("API_ENDPOINT", ""))
        aws_region = st.text_input("AWS Region", value=os.environ.get("AWS_REGION", "us-east-1"))
    return {
        "s3_bucket": s3_bucket,
        "s3_prefix": s3_prefix,
        "api_endpoint": api_endpoint,
        "aws_region": aws_region,
    }


def render_tool_log(tool_log: list):
    """Render the captured tool log with thinking steps and tool calls."""
    for entry in tool_log:
        entry_type = entry.get("type", "")

        if entry_type == "thinking":
            st.info(f"💭 {entry['text']}")

        elif entry_type == "tool_call":
            tool_name = entry.get("name", "unknown")
            tool_input = entry.get("input", {})
            tool_num = entry.get("tool_number", "?")
            label = TOOL_LABELS.get(tool_name, f"🔧 {tool_name}")

            with st.expander(f"🔧 Tool #{tool_num}: {label}", expanded=True):
                try:
                    st.code(json.dumps(tool_input, indent=2, default=str), language="json")
                except Exception:
                    st.code(str(tool_input), language="text")


def main():
    st.set_page_config(page_title="Contract Workflow Agent", page_icon="📄", layout="wide")
    st.title("📄 Contract Workflow Agent")

    config = build_sidebar_config()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message.get("tool_log"):
                with st.expander("📋 Agent execution trace", expanded=False):
                    render_tool_log(message["tool_log"])
            st.markdown(message["content"])

    user_input = st.chat_input("Describe your contract workflow request...")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            tool_log = []
            response_text = ""

            with st.status("🤖 Agent is processing...", expanded=True) as status:
                st.write("Invoking agent...")
                try:
                    agent = create_agent(config, tool_log=tool_log)
                    result = agent(user_input)
                    response_text = str(result)
                    # Show summary of what happened inside the status
                    tool_calls = [e for e in tool_log if e.get("type") == "tool_call"]
                    for tc in tool_calls:
                        name = tc.get("name", "unknown")
                        label = TOOL_LABELS.get(name, name)
                        st.write(f"✅ {label}")
                    status.update(label="✅ Agent completed", state="complete", expanded=False)
                except Exception as e:
                    response_text = f"❌ An error occurred: {e}"
                    status.update(label="❌ Error", state="error")

            # Show detailed trace
            if tool_log:
                with st.expander("📋 Agent execution trace", expanded=True):
                    render_tool_log(tool_log)

            st.markdown(response_text)

        st.session_state.messages.append({
            "role": "assistant",
            "content": response_text,
            "tool_log": tool_log,
        })


if __name__ == "__main__":
    main()
