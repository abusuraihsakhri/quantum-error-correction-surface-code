"""
FastAPI REST API Server for Surface Code Quantum Error Correction & Minimum Weight Matching Agent.
"""
from typing import Dict, Any
from .models import FrontierPayload
from .agents import SurfaceCodeCoordinator

coordinator = SurfaceCodeCoordinator()


def create_app():
    try:
        from fastapi import FastAPI, HTTPException
        from pydantic import BaseModel, Field
        from pathlib import Path
        from fastapi.responses import FileResponse
        from fastapi.staticfiles import StaticFiles
        from .engine import error_correction_cycle, calculate_logical_error_rate, code_properties

        app = FastAPI(
            title="Surface Code Quantum Error Correction & Minimum Weight Matching Agent",
            description="Decodes 2D rotated surface code syndrome measurements using Blossom minimum-weight perfect matching (MWPM) algorithms.",
            version="2.0.0-FRONTIER",
        )

        class TaskRequest(BaseModel):
            task_id: str = "TASK-2026-001"
            target_identifier: str = "TARGET-BIO-KEY"
            primary_metric: float = 28.5
            secondary_metric: float = 14.2
            status_descriptor: str = "DISCORDANT_ANOMALY"
            is_critical_flag: bool = True
            attributes: Dict[str, Any] = {}

        class SimulationRequest(BaseModel):
            distance: int = Field(default=3, ge=3, le=21)
            error_rate: float = Field(default=0.01, ge=0, le=1, allow_inf_nan=False)
            seed: int = 42

        class RateRequest(SimulationRequest):
            trials: int = Field(default=100, ge=1, le=100000)

        class ChatRequest(BaseModel):
            query: str

        @app.get("/health")
        def health():
            return {"status": "HEALTHY", "system": "quantum-error-correction-surface-code", "domain": "Quantum Computing", "version": "2.0.0-FRONTIER"}

        @app.post("/api/audit")
        def api_audit(req: TaskRequest):
            payload = FrontierPayload(
                task_id=req.task_id,
                target_identifier=req.target_identifier,
                primary_metric=req.primary_metric,
                secondary_metric=req.secondary_metric,
                status_descriptor=req.status_descriptor,
                is_critical_flag=req.is_critical_flag,
                attributes=req.attributes,
            )
            return coordinator.process(payload)

        @app.post("/api/chat")
        def api_chat(req: ChatRequest):
            return {"response": coordinator.query_supervisory_chat(req.query)}

        @app.post("/api/qec/cycle")
        def qec_cycle(req: SimulationRequest):
            if req.distance % 2 == 0:
                raise HTTPException(status_code=422, detail="Distance must be odd")
            return error_correction_cycle(req.distance, req.error_rate, seed=req.seed)

        @app.post("/api/qec/rate")
        def qec_rate(req: RateRequest):
            if req.distance % 2 == 0:
                raise HTTPException(status_code=422, detail="Distance must be odd")
            return calculate_logical_error_rate(req.distance, req.error_rate, req.trials, req.seed)

        @app.get("/api/qec/properties/{distance}")
        def qec_properties(distance: int):
            if distance < 3 or distance > 21 or distance % 2 == 0:
                raise HTTPException(status_code=422, detail="Distance must be odd and between 3 and 21")
            return code_properties(distance)

        # Keep the browser UI usable when served from the Python backend.
        frontend = Path(__file__).resolve().parent.parent / "web"
        if frontend.is_dir():
            @app.get("/engine.py")
            def browser_engine():
                return FileResponse(Path(__file__).with_name("engine.py"), media_type="text/plain")

            app.mount("/", StaticFiles(directory=str(frontend), html=True), name="frontend")

        return app
    except ImportError:
        return None
