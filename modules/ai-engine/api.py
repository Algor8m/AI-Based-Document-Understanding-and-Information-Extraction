
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.analyzer import analyze_document

app = FastAPI(
    title="IVP+AI Document Understanding API",
    description="Extract facts and derive information from document text.",
    version="1.0.0",
)


class AnalyzeRequest(BaseModel):
    document_id: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)


@app.get("/")
def health_check():
    return {
        "status": "running",
        "service": "IVP+AI AI Engine",
        "version": "1.0.0",
    }


@app.post("/api/v1/analyze")
def analyze(request: AnalyzeRequest):
    try:
        return analyze_document(
            document_id=request.document_id,
            text=request.text,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Document analysis failed.",
        ) from error
