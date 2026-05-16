"""
Paper management endpoints.
"""
from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Query
from fastapi.responses import JSONResponse

from app.models.schemas import (
    PaperUploadResponse,
    PaperInfo,
    ErrorResponse,
)
from app.services.document_service import DocumentService
from app.api.deps import get_document_service, get_request_id
from app.core.config import settings
from app.core.exceptions import (
    DocumentProcessingError,
    PaperNotFoundError,
    ValidationError,
)
from app.utils.logger import app_logger


router = APIRouter(prefix="/papers", tags=["Papers"])


@router.post("/upload", response_model=PaperUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_paper(
    file: UploadFile = File(..., description="PDF file to upload"),
    document_service: DocumentService = Depends(get_document_service),
    request_id: str = Depends(get_request_id),
) -> PaperUploadResponse:
    """
    Upload and process a research paper PDF.
    
    **Process:**
    1. Validate file type and size
    2. Extract text and metadata
    3. Chunk document intelligently
    4. Generate embeddings
    5. Index in Qdrant Cloud
    
    **Args:**
    - **file**: PDF file (max 50MB by default)
    
    **Returns:**
    - Paper ID, metadata, and processing status
    
    **Raises:**
    - 400: Invalid file type or size
    - 422: Processing error
    - 500: Server error
    """
    app_logger.info(f"Uploading paper: {file.filename}")
    
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise ValidationError(
            "Invalid file type",
            detail="Only PDF files are supported"
        )
    
    # Validate file size
    file_content = await file.read()
    file_size = len(file_content)
    
    if file_size > settings.max_upload_size_bytes:
        raise ValidationError(
            "File too large",
            detail=f"Maximum file size is {settings.max_upload_size_mb}MB"
        )
    
    if file_size == 0:
        raise ValidationError(
            "Empty file",
            detail="Uploaded file is empty"
        )
    
    try:
        # Process document
        response = await document_service.process_document(
            file_content=file_content,
            filename=file.filename,
        )
        
        app_logger.info(
            f"Paper uploaded successfully: {response.paper_id}",
            extra={"paper_id": response.paper_id, "num_chunks": response.num_chunks}
        )
        
        return response
        
    except DocumentProcessingError as e:
        app_logger.error(f"Document processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": e.message, "detail": e.detail}
        )
    except Exception as e:
        app_logger.error(f"Unexpected error during upload: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error", "detail": str(e)}
        )


@router.get("/{paper_id}", response_model=PaperInfo)
async def get_paper(
    paper_id: str,
    document_service: DocumentService = Depends(get_document_service),
    request_id: str = Depends(get_request_id),
) -> PaperInfo:
    """
    Get information about a specific paper.
    
    **Args:**
    - **paper_id**: Unique paper identifier
    
    **Returns:**
    - Paper metadata and information
    
    **Raises:**
    - 404: Paper not found
    - 500: Server error
    """
    try:
        paper_info = await document_service.get_paper_info(paper_id)
        
        if paper_info is None:
            raise PaperNotFoundError(
                f"Paper not found: {paper_id}",
                detail="The requested paper does not exist"
            )
        
        return paper_info
        
    except PaperNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": e.message, "detail": e.detail}
        )
    except Exception as e:
        app_logger.error(f"Error retrieving paper {paper_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error", "detail": str(e)}
        )


@router.get("", response_model=List[PaperInfo])
async def list_papers(
    skip: int = Query(0, ge=0, description="Number of papers to skip"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of papers to return"),
    document_service: DocumentService = Depends(get_document_service),
    request_id: str = Depends(get_request_id),
) -> List[PaperInfo]:
    """
    List all uploaded papers with pagination.
    
    **Args:**
    - **skip**: Number of papers to skip (default: 0)
    - **limit**: Maximum papers to return (default: 10, max: 100)
    
    **Returns:**
    - List of paper information
    
    **Raises:**
    - 500: Server error
    """
    try:
        papers = await document_service.list_papers(skip=skip, limit=limit)
        return papers
        
    except Exception as e:
        app_logger.error(f"Error listing papers: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error", "detail": str(e)}
        )


@router.delete("/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_paper(
    paper_id: str,
    document_service: DocumentService = Depends(get_document_service),
    request_id: str = Depends(get_request_id),
) -> None:
    """
    Delete a paper and all its associated data.
    
    **Args:**
    - **paper_id**: Unique paper identifier
    
    **Returns:**
    - 204 No Content on success
    
    **Raises:**
    - 404: Paper not found
    - 500: Server error
    """
    try:
        success = await document_service.delete_paper(paper_id)
        
        if not success:
            raise PaperNotFoundError(
                f"Paper not found: {paper_id}",
                detail="The requested paper does not exist"
            )
        
        app_logger.info(f"Paper deleted: {paper_id}")
        
    except PaperNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": e.message, "detail": e.detail}
        )
    except Exception as e:
        app_logger.error(f"Error deleting paper {paper_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Internal server error", "detail": str(e)}
        )
