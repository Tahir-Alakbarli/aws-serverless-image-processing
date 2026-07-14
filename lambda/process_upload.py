import json
import os
import re
from datetime import datetime, timezone
from urllib.parse import unquote_plus

import boto3


s3 = boto3.client("s3")


def lambda_handler(event, context):
    processed = []

    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        source_key = unquote_plus(record["s3"]["object"]["key"])

        # The S3 trigger should already filter for uploads/, but this check adds safety.
        if not source_key.startswith("uploads/"):
            continue

        original_name = os.path.basename(source_key)
        clean_name = re.sub(r"[^a-zA-Z0-9._-]+", "-", original_name).lower()
        processed_key = f"processed/processed-{clean_name}"
        metadata_key = f"metadata/{clean_name}.json"

        source_head = s3.head_object(Bucket=bucket, Key=source_key)
        content_type = source_head.get("ContentType", "application/octet-stream")
        size = record["s3"]["object"].get("size", source_head.get("ContentLength", 0))

        s3.copy_object(
            Bucket=bucket,
            CopySource={"Bucket": bucket, "Key": source_key},
            Key=processed_key,
            ContentType=content_type,
            MetadataDirective="REPLACE",
            Metadata={
                "processing-status": "processed",
                "original-key": source_key,
            },
        )

        receipt = {
            "status": "processed",
            "originalKey": source_key,
            "processedKey": processed_key,
            "contentType": content_type,
            "sizeBytes": size,
            "processedAt": datetime.now(timezone.utc).isoformat(),
        }

        s3.put_object(
            Bucket=bucket,
            Key=metadata_key,
            Body=json.dumps(receipt, indent=2).encode("utf-8"),
            ContentType="application/json",
        )

        processed.append(receipt)
        print(json.dumps({"event": "image_processed", **receipt}))

    return {"processed": processed}
