"""
Document conversion API endpoints - placeholder.
"""

from django.http import HttpRequest
from ninja import Router, UploadedFile, File
from ninja.errors import HttpError

from utils.auth import AuthBearer, get_current_user
from .schemas import ConvertJobOut, ConvertStatusOut

router = Router(auth=AuthBearer())


@router.post("/word-to-pdf", response=ConvertJobOut)
def convert_word_to_pdf(request: HttpRequest, file: UploadedFile = File(...)):
    """Convert Word document to PDF."""
    user = get_current_user(request)

    # TODO: Implement actual conversion using LibreOffice or similar
    # This is a placeholder

    return ConvertJobOut(
        job_id="placeholder",
        status="pending",
        download_url=None,
    )


@router.post("/pdf-to-word", response=ConvertJobOut)
def convert_pdf_to_word(request: HttpRequest, file: UploadedFile = File(...)):
    """Convert PDF to Word document."""
    user = get_current_user(request)

    # TODO: Implement actual conversion
    # This is a placeholder

    return ConvertJobOut(
        job_id="placeholder",
        status="pending",
        download_url=None,
    )


@router.get("/status/{job_id}", response=ConvertStatusOut)
def get_conversion_status(request: HttpRequest, job_id: str):
    """Get conversion job status."""
    # TODO: Implement actual status tracking

    return ConvertStatusOut(
        status="pending",
        download_url=None,
        error=None,
    )
