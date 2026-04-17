"""Health check endpoint."""

from fastapi import APIRouter

from uso import __version__
from uso.models import HealthOut

router = APIRouter()


@router.get("/health", response_model=HealthOut)
def health_check():
    return HealthOut(status="ok", version=__version__)
