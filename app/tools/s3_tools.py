"""S3 file download tool."""

import boto3
from botocore.exceptions import ClientError, EndpointConnectionError
from strands.tools import tool


@tool
def download_s3_file(transaction_id: str, s3_bucket: str, s3_prefix: str, aws_region: str) -> dict:
    """
    Download an Excel file from S3.

    Constructs the S3 key as {s3_prefix}/{transaction_id}.xlsx and downloads
    the file to /tmp/{transaction_id}.xlsx using boto3.

    Args:
        transaction_id: The transaction ID (e.g. 12345).
        s3_bucket: The S3 bucket name.
        s3_prefix: The S3 key prefix (folder path).
        aws_region: The AWS region for the S3 client.

    Returns:
        {"status": "success", "file_path": "/tmp/process_12345.xlsx"}
        or {"status": "error", "error_type": "...", "message": "..."}
    """
    s3_key = f"{s3_prefix}/process_{transaction_id}.xlsx" if s3_prefix else f"process_{transaction_id}.xlsx"
    local_path = f"/tmp/process_{transaction_id}.xlsx"

    try:
        s3_client = boto3.client("s3", region_name=aws_region)
        s3_client.download_file(s3_bucket, s3_key, local_path)
        return {"status": "success", "file_path": local_path}
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code == "NoSuchKey" or error_code == "404":
            return {
                "status": "error",
                "error_type": "FileNotFoundError",
                "message": f"File not found at s3://{s3_bucket}/{s3_key}",
            }
        elif error_code == "AccessDenied" or error_code == "403":
            return {
                "status": "error",
                "error_type": "PermissionError",
                "message": (
                    f"Access denied when downloading s3://{s3_bucket}/{s3_key}. "
                    "Check that the IAM role or credentials have s3:GetObject permission on this resource."
                ),
            }
        else:
            return {
                "status": "error",
                "error_type": "ClientError",
                "message": f"S3 client error downloading s3://{s3_bucket}/{s3_key}: {e}",
            }
    except EndpointConnectionError as e:
        return {
            "status": "error",
            "error_type": "ConnectionError",
            "message": (
                f"Could not connect to S3 endpoint while downloading s3://{s3_bucket}/{s3_key}. "
                f"Check your network connection and region setting. Details: {e}"
            ),
        }
    except Exception as e:
        return {
            "status": "error",
            "error_type": type(e).__name__,
            "message": f"Unexpected error downloading s3://{s3_bucket}/{s3_key}: {e}",
        }
