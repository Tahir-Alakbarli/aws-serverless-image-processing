import base64
import json
import os
import re
import uuid

import boto3


s3 = boto3.client("s3")
UPLOAD_BUCKET = os.environ["UPLOAD_BUCKET"]
MAX_FILE_SIZE = 5 * 1024 * 1024

ALLOWED_TYPES = {
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
    "image/webp": {".webp"},
}


def response(status_code, payload):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload),
    }


def lambda_handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method")
    if method != "POST":
        return response(405, {"message": "Use POST for this endpoint."})

    try:
        raw_body = event.get("body") or "{}"
        if event.get("isBase64Encoded"):
            raw_body = base64.b64decode(raw_body).decode("utf-8")
        body = json.loads(raw_body)
    except (ValueError, UnicodeDecodeError):
        return response(400, {"message": "The request body must be valid JSON."})

    original_name = str(body.get("fileName", "")).strip()
    content_type = str(body.get("fileType", "")).strip().lower()

    if not original_name or content_type not in ALLOWED_TYPES:
        return response(400, {"message": "Choose a JPG, PNG, or WebP image."})

    extension = os.path.splitext(original_name)[1].lower()
    if extension not in ALLOWED_TYPES[content_type]:
        return response(400, {"message": "The file extension does not match the image type."})

    base_name = os.path.splitext(os.path.basename(original_name))[0]
    safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "-", base_name).strip("-").lower()
    safe_name = safe_name[:60] or "image"
    object_key = f"uploads/{uuid.uuid4().hex[:12]}-{safe_name}{extension}"

    presigned_post = s3.generate_presigned_post(
        Bucket=UPLOAD_BUCKET,
        Key=object_key,
        Fields={"Content-Type": content_type},
        Conditions=[
            {"Content-Type": content_type},
            ["content-length-range", 1, MAX_FILE_SIZE],
        ],
        ExpiresIn=120,
    )

    print(json.dumps({"event": "upload_permission_created", "objectKey": object_key}))

    return response(
        200,
        {
            "uploadUrl": presigned_post["url"],
            "fields": presigned_post["fields"],
            "objectKey": object_key,
            "expiresIn": 120,
        },
    )
