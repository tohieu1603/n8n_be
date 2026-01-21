"""
Document conversion schemas for API.
"""

from ninja import Schema, UploadedFile


class ConvertJobOut(Schema):
    job_id: str
    status: str
    download_url: str | None = None


class ConvertStatusOut(Schema):
    status: str
    download_url: str | None = None
    error: str | None = None
