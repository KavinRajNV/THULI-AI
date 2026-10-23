"""
app/storage.py — Wrapper module for S3 storage integration.
Imports all symbols from backend.storage for standardized access.
"""

import os
import sys

# Ensure backend directory is in sys.path
_current_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.join(os.path.dirname(_current_dir), "backend")
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

try:
    from storage import (
        S3_BUCKET,
        S3_MODEL_PREFIX,
        S3_AUDIO_PREFIX,
        S3_UPLOAD_AUDIO,
        AWS_REGION,
        get_s3_client,
        is_s3_configured,
        is_audio_upload_enabled,
        download_models_from_s3,
        upload_file_to_s3,
        upload_call_audio,
    )
except ImportError:
    # Direct relative fallback if running within backend
    from backend.storage import (  # type: ignore
        S3_BUCKET,
        S3_MODEL_PREFIX,
        S3_AUDIO_PREFIX,
        S3_UPLOAD_AUDIO,
        AWS_REGION,
        get_s3_client,
        is_s3_configured,
        is_audio_upload_enabled,
        download_models_from_s3,
        upload_file_to_s3,
        upload_call_audio,
    )

__all__ = [
    "S3_BUCKET",
    "S3_MODEL_PREFIX",
    "S3_AUDIO_PREFIX",
    "S3_UPLOAD_AUDIO",
    "AWS_REGION",
    "get_s3_client",
    "is_s3_configured",
    "is_audio_upload_enabled",
    "download_models_from_s3",
    "upload_file_to_s3",
    "upload_call_audio",
]
