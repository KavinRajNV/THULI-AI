"""
storage.py — AWS S3 integration for Thuli AI (KISAN.AI).

Provides:
1. Startup download of ML model artifacts from S3 with local-disk fallback.
2. Optional background upload of Exotel call audio recordings to S3.
3. IAM task-role compatible (no hardcoded credentials required on ECS Fargate).

Environment Variables:
- S3_BUCKET        : Name of the S3 bucket (e.g. "<S3_BUCKET_NAME>"). If empty, falls back to local disk.
- S3_MODEL_PREFIX : S3 key prefix for models (default: "models/").
- S3_AUDIO_PREFIX : S3 key prefix for call recordings (default: "audio/calls/").
- S3_UPLOAD_AUDIO : "true" to enable audio upload to S3 (default: "false").
- AWS_REGION       : AWS region (default: "ap-south-1").
"""

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger("thuli.storage")

# Configuration from environment variables
S3_BUCKET = os.getenv("S3_BUCKET", "").strip()
_raw_model_prefix = os.getenv("S3_MODEL_PREFIX", "models/").strip()
S3_MODEL_PREFIX = _raw_model_prefix if _raw_model_prefix.endswith("/") or not _raw_model_prefix else f"{_raw_model_prefix}/"

_raw_audio_prefix = os.getenv("S3_AUDIO_PREFIX", "audio/calls/").strip()
S3_AUDIO_PREFIX = _raw_audio_prefix if _raw_audio_prefix.endswith("/") or not _raw_audio_prefix else f"{_raw_audio_prefix}/"

S3_UPLOAD_AUDIO = os.getenv("S3_UPLOAD_AUDIO", "false").strip().lower() in ("true", "1", "yes", "on")
AWS_REGION = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "ap-south-1")).strip()

# Lazy S3 client cache
_s3_client = None


def safe_print(msg: str):
    """Safely print messages, avoiding UnicodeEncodeError on cp1252 Windows consoles."""
    try:
        print(msg)
    except UnicodeEncodeError:
        try:
            print(msg.encode("ascii", errors="replace").decode("ascii"))
        except Exception:
            pass


def get_s3_client():
    """
    Get or initialize a boto3 S3 client.
    Uses AWS ECS Task Role credentials automatically when running on Fargate,
    or standard AWS credential chain (env vars / AWS profile) locally.
    """
    global _s3_client
    if _s3_client is not None:
        return _s3_client

    try:
        import boto3
        _s3_client = boto3.client("s3", region_name=AWS_REGION or "ap-south-1")
        return _s3_client
    except Exception as e:
        logger.warning(f"Could not initialize boto3 S3 client: {e}")
        return None


def is_s3_configured() -> bool:
    """Return True if S3_BUCKET is set and non-empty."""
    return bool(S3_BUCKET and S3_BUCKET != "<S3_BUCKET_NAME>")


def is_audio_upload_enabled() -> bool:
    """Return True if audio recording upload to S3 is explicitly enabled."""
    return is_s3_configured() and S3_UPLOAD_AUDIO


def download_models_from_s3(target_base_dir: Optional[str] = None) -> bool:
    """
    Download ML model artifacts and datasets from S3 at startup.
    If S3_BUCKET is not set or fails, gracefully falls back to local disk files.

    Returns:
        bool: True if downloaded from S3, False if local fallback was used.
    """
    if not is_s3_configured():
        safe_print("[Storage] S3_BUCKET is not set. Using local disk ML model artifacts (fallback mode).")
        return False

    client = get_s3_client()
    if client is None:
        safe_print("[Storage] S3 client unavailable. Falling back to local disk.")
        return False

    if target_base_dir is None:
        # Resolve to backend root directory
        target_base_dir = str(Path(__file__).resolve().parent)

    safe_print(f"[Storage] Connecting to s3://{S3_BUCKET}/{S3_MODEL_PREFIX} in {AWS_REGION}...")

    try:
        paginator = client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=S3_BUCKET, Prefix=S3_MODEL_PREFIX)

        downloaded_count = 0
        skipped_count = 0

        for page in pages:
            for obj in page.get("Contents", []):
                key = obj["Key"]
                # Skip folder placeholder keys
                if key.endswith("/"):
                    continue

                # Compute relative destination path inside target_base_dir
                rel_path = key[len(S3_MODEL_PREFIX):] if key.startswith(S3_MODEL_PREFIX) else key
                dest_path = Path(target_base_dir) / rel_path

                dest_path.parent.mkdir(parents=True, exist_ok=True)

                remote_size = obj.get("Size", 0)
                if dest_path.exists() and dest_path.stat().st_size == remote_size:
                    skipped_count += 1
                    continue

                safe_print(f"   Downloading {key} -> {dest_path.name} ({remote_size / (1024*1024):.2f} MB)...")
                client.download_file(S3_BUCKET, key, str(dest_path))
                downloaded_count += 1

        safe_print(f"[Storage] S3 model sync complete: {downloaded_count} downloaded, {skipped_count} up-to-date.")
        return True

    except Exception as e:
        safe_print(f"[Storage] Error syncing models from S3 ({e}). Continuing with local disk fallback.")
        return False



def upload_file_to_s3(
    local_path: str,
    s3_key: Optional[str] = None,
    content_type: Optional[str] = None
) -> Optional[str]:
    """
    Upload a local file to S3.

    Args:
        local_path: Absolute or relative path to the local file.
        s3_key: Destination key in S3. Defaults to S3_AUDIO_PREFIX + filename.
        content_type: MIME type of the file.

    Returns:
        S3 URI (e.g. 's3://bucket/key') on success, or None on failure/skip.
    """
    if not is_s3_configured():
        return None

    path_obj = Path(local_path)
    if not path_obj.exists():
        logger.warning(f"⚠️  [Storage] File to upload does not exist: {local_path}")
        return None

    if s3_key is None:
        s3_key = f"{S3_AUDIO_PREFIX}{path_obj.name}"

    client = get_s3_client()
    if client is None:
        return None

    extra_args = {}
    if content_type:
        extra_args["ContentType"] = content_type
    else:
        suffix = path_obj.suffix.lower()
        if suffix == ".webm":
            extra_args["ContentType"] = "audio/webm"
        elif suffix == ".mp3":
            extra_args["ContentType"] = "audio/mpeg"
        elif suffix == ".wav":
            extra_args["ContentType"] = "audio/wav"

    try:
        client.upload_file(
            Filename=str(path_obj),
            Bucket=S3_BUCKET,
            Key=s3_key,
            ExtraArgs=extra_args if extra_args else None,
        )
        s3_uri = f"s3://{S3_BUCKET}/{s3_key}"
        logger.info(f"✅ [Storage] Uploaded audio to {s3_uri}")
        return s3_uri
    except Exception as e:
        logger.warning(f"⚠️  [Storage] Failed to upload {local_path} to S3: {e}")
        return None


def upload_call_audio(
    local_path: str,
    call_sid: str = "",
    speaker: str = "farmer"
) -> Optional[str]:
    """
    Convenience wrapper for uploading Exotel call recordings.
    Only executes if S3_UPLOAD_AUDIO is enabled.
    Intended to be dispatched via FastAPI BackgroundTasks so it never
    blocks the Exotel response.
    """
    if not is_audio_upload_enabled():
        return None

    filename = Path(local_path).name
    s3_key = f"{S3_AUDIO_PREFIX}{filename}"
    return upload_file_to_s3(local_path, s3_key=s3_key)
