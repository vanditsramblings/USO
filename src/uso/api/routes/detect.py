"""Script auto-detection API route."""

from fastapi import APIRouter
from pydantic import BaseModel

from uso.detector import detect
from uso.models import DetectionResult

router = APIRouter()


class DetectRequest(BaseModel):
    content: str
    runtime: str


@router.post("", response_model=DetectionResult)
def detect_script(data: DetectRequest):
    return detect(data.content, data.runtime)
