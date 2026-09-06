from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.core.security import require_role, authorize_investigation_access
from app.services.report_service import ReportService

router = APIRouter()


@router.get("/{investigation_id}/json")
def get_json_dossier(
    investigation_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("LEAD_AUDITOR", "CTI_ANALYST"))
):
    """
    Exports a comprehensive, tamper-evident JSON dossier reconstructed purely
    from persisted database models in accordance with Decision #11.
    """
    authorize_investigation_access(investigation_id, current_user, db)
    try:
        return ReportService.generate_json_dossier(investigation_id, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Dossier generation failed: {str(e)}")


@router.get("/{investigation_id}/csv")
def get_csv_dossier(
    investigation_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("LEAD_AUDITOR", "CTI_ANALYST"))
):
    """
    Exports a deterministic multi-section CSV dossier of the investigation,
    artifacts, entities, sources, and audit ledger.
    """
    authorize_investigation_access(investigation_id, current_user, db)
    try:
        csv_content = ReportService.generate_csv_dossier(investigation_id, db)
        filename = f"TRACE-X_Dossier_{investigation_id}.csv"
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"CSV export failed: {str(e)}")


@router.get("/{investigation_id}/pdf")
def get_pdf_dossier(
    investigation_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role("LEAD_AUDITOR", "CTI_ANALYST"))
):
    """
    Generates and downloads a publication-grade Forensic Investigation Dossier PDF
    with NTRO headers, permanent disclaimers, 5-dimension radar breakdown,
    model provenance, and cryptographic audit ledger.
    """
    authorize_investigation_access(investigation_id, current_user, db)
    try:
        pdf_bytes = ReportService.generate_pdf_dossier(investigation_id, db)
        filename = f"TRACE-X_Dossier_{investigation_id}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"PDF generation failed: {str(e)}")
