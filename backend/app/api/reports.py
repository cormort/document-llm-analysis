"""Report Generation API endpoints."""

import os
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
import structlog

logger = structlog.get_logger(__name__)
from fastapi.responses import FileResponse

from app.models.reports import ReportGenerateRequest, ReportResponse, SkillInfo
from app.services.llm_service import llm_service
from app.services.report_exporter import generate_docx_report
from app.services.skills_registry import REPORT_TEMPLATES, SKILLS, get_skills_by_ids

router = APIRouter()

# Upload directory path
UPLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data",
    "uploads",
)


@router.get("/templates")
async def list_templates() -> list[dict]:
    """List all available report templates with recommended skills."""
    try:
        return [
            {
                "id": template_id,
                "name": data["name"],
                "description": data["description"],
                "recommended_skills": data["recommended_skills"],
            }
            for template_id, data in REPORT_TEMPLATES.items()
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/skills", response_model=list[SkillInfo])
async def list_skills() -> list[SkillInfo]:
    """List all available expert skills."""
    try:
        return [
            SkillInfo(
                id=skill_id,
                name=skill.name,
                description=skill.description,
                category=skill.category,
                prompt_fragment=skill.prompt_fragment,
            )
            for skill_id, skill in SKILLS.items()
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/generate", response_model=ReportResponse)
async def generate_report(request: ReportGenerateRequest) -> ReportResponse:
    """Generate a professional report using LLM and Agent Skills."""
    try:
        logger.info("Report Generation Started", template=request.template_name)
        

        selected_skill_objs = get_skills_by_ids(request.selected_skills)
        skills_text = "\n".join([s.prompt_fragment for s in selected_skill_objs])

        full_instruction = f"Template: {request.template_name}\nSkills:\n{skills_text}\n\n{request.user_instruction}"

        if request.file_path:
            # Resolve the file path - check if it's already absolute or just filename
            file_path = request.file_path
            if not os.path.isabs(file_path):
                # Try to find in uploads directory
                upload_path = os.path.join(UPLOAD_DIR, file_path)
                if os.path.exists(upload_path):
                    file_path = upload_path
                else:
                    # Try current working directory
                    cwd_path = os.path.join(os.getcwd(), file_path)
                    if os.path.exists(cwd_path):
                        file_path = cwd_path

            # Enable black-faced auditor mode for financial template
            is_financial_audit = request.template_name == "financial"

            content = await llm_service.analyze_file(
                file_path=file_path,
                user_instruction=full_instruction,
                provider=request.config.provider,
                model_name=request.config.model_name,
                local_url=request.config.local_url,
                context_window=request.config.context_window,
                financial_skepticism=is_financial_audit,
                api_key=request.config.api_key,
            )
        else:
            content = await llm_service.analyze_text(
                text_content="No source file provided",
                user_instruction=full_instruction,
                provider=request.config.provider,
                model_name=request.config.model_name,
                local_url=request.config.local_url,
                context_window=request.config.context_window,
            )

        logger.info(
            "LLM Analysis Completed", content_len=len(content) if content else 0
        )

        try:
            response = ReportResponse(
                report_id="rep_placeholder", content=content, docx_path=None
            )
            logger.info("ReportResponse Created Successfully")
            return response
        except Exception as pydantic_err:
            logger.error(
                "Pydantic Validation Error in ReportResponse", error=str(pydantic_err)
            )
            raise

    except Exception as e:
        import traceback

        error_trace = traceback.format_exc()
        logger.error("Report Generation Failed", error=str(e), traceback=error_trace)
        raise HTTPException(
            status_code=500, detail=f"Internal Server Error: {str(e)}"
        ) from e


@router.post("/download")
async def download_report_docx(request: dict, background_tasks: BackgroundTasks):
    """Convert report content to docx and download."""
    try:
        content = request.get("content", "")
        title = request.get("title", "AI 分析報告")

        # Create a temporary file
        temp_file = NamedTemporaryFile(delete=False, suffix=".docx")
        temp_path = temp_file.name
        temp_file.close()

        # Generate docx
        generate_docx_report(title, content, output_path=temp_path)

        # Clean up temporary file after sending
        background_tasks.add_task(os.unlink, temp_path)

        return FileResponse(
            path=temp_path,
            filename=f"{title.replace(' ', '_')}.docx",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
