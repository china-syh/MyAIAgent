"""Durable orchestration for the project's end-to-end production line."""
import asyncio
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.planner import PlanningAgent
from app.agents.writer import WritingAgent
from app.agents.storyboarder import StoryboardAgent
from app.agents.prompter import PromptAgent
from app.agents.quality_checker import QualityCheckerAgent
from app.repositories import CharacterRepository, ProductionRunRepository, ProductionStageRepository, ProjectRepository
from app.services.script_service import ScriptService

STAGES = ("planning", "writing", "storyboarding", "prompting", "quality")


class ProductionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.run_repo = ProductionRunRepository(db)
        self.stage_repo = ProductionStageRepository(db)
        self.project_repo = ProjectRepository(db)
        self.character_repo = CharacterRepository(db)

    async def start(self, project_id: str, story_input: str = "", genre: str = "fantasy", stages: list[str] | None = None):
        project_id_obj = UUID(project_id)
        project = await self.project_repo.get(project_id_obj)
        if not project:
            return None
        existing = await self.run_repo.get_latest_by_project(project_id_obj)
        if existing and existing.status in {"pending", "running", "paused"}:
            return await self.get(str(existing.id))
        selected = [name for name in (stages or list(STAGES)) if name in STAGES] or list(STAGES)
        run = await self.run_repo.create(
            project_id=project_id_obj, status="pending", current_stage=selected[0],
            input_snapshot={"story_input": story_input or project.story_input, "genre": genre or project.genre, "stages": selected},
            output={}, error="",
        )
        for order, name in enumerate(selected):
            await self.stage_repo.create(run_id=run.id, name=name, order=order, status="pending", input_data={}, output_data={}, error="")
        await self.project_repo.update(project_id_obj, status="generating")
        asyncio.create_task(self._run(str(run.id)))
        return await self.get(str(run.id))

    async def get(self, run_id: str):
        run = await self.run_repo.get(UUID(run_id))
        if not run:
            return None
        stages = await self.stage_repo.get_by_run(run.id)
        return {"id": run.id, "project_id": run.project_id, "status": run.status, "current_stage": run.current_stage,
                "input_snapshot": run.input_snapshot or {}, "output": run.output or {}, "error": run.error or "",
                "created_at": run.created_at, "updated_at": run.updated_at,
                "stages": [{"id": s.id, "run_id": s.run_id, "name": s.name, "order": s.order, "status": s.status,
                            "input_data": s.input_data or {}, "output_data": s.output_data or {}, "error": s.error or "",
                            "started_at": s.started_at, "completed_at": s.completed_at} for s in stages]}

    async def pause(self, run_id: str):
        run = await self.run_repo.update(UUID(run_id), status="paused")
        return await self.get(run_id) if run else None

    async def resume(self, run_id: str):
        run = await self.run_repo.get(UUID(run_id))
        if not run:
            return None
        if run.status in {"paused", "failed"}:
            await self.run_repo.update(run.id, status="running", error="")
            asyncio.create_task(self._run(run_id))
        return await self.get(run_id)

    async def retry_stage(self, run_id: str, stage_name: str):
        run = await self.run_repo.get(UUID(run_id))
        stages = await self.stage_repo.get_by_run(UUID(run_id)) if run else []
        stage = next((item for item in stages if item.name == stage_name), None)
        if not run or not stage or stage.name != stage_name:
            return None
        for item in stages:
            if item.order >= stage.order:
                await self.stage_repo.update(item.id, status="pending", error="", output_data={}, completed_at=None)
        await self.run_repo.update(run.id, status="running", current_stage=stage_name, error="")
        asyncio.create_task(self._run(run_id))
        return await self.get(run_id)

    async def _run(self, run_id: str):
        from app.database import async_session
        async with async_session() as db:
            runner = ProductionService(db)
            run = await runner.run_repo.get(UUID(run_id))
            if not run or run.status == "paused":
                return
            try:
                context: dict[str, Any] = {"project_id": str(run.project_id), "story_input": run.input_snapshot.get("story_input", ""),
                                           "genre": run.input_snapshot.get("genre", "fantasy"), "characters": []}
                stage_map = {s.name: s for s in await runner.stage_repo.get_by_run(run.id)}
                agents = {"planning": PlanningAgent(), "writing": WritingAgent(), "storyboarding": StoryboardAgent(),
                          "prompting": PromptAgent(), "quality": QualityCheckerAgent()}
                for name in run.input_snapshot.get("stages", list(STAGES)):
                    stage = stage_map.get(name)
                    if not stage:
                        continue
                    if stage.status == "completed":
                        context.update(stage.output_data or {})
                        continue
                    latest = await runner.run_repo.get(run.id)
                    if not latest or latest.status == "paused":
                        return
                    await runner.run_repo.update(run.id, current_stage=name, status="running")
                    await runner.stage_repo.update(stage.id, status="running", started_at=datetime.now(timezone.utc), input_data=context)
                    result = await asyncio.to_thread(agents[name].run, context)
                    if result.get("error"):
                        await runner.stage_repo.update(stage.id, status="failed", error=result["error"])
                        await runner.run_repo.update(run.id, status="failed", error=result["error"])
                        await runner.project_repo.update(run.project_id, status="failed")
                        return
                    context.update(result)
                    await runner._persist_stage_output(run, name, context)
                    await runner.stage_repo.update(stage.id, status="completed", output_data=result, completed_at=datetime.now(timezone.utc))
                await runner.run_repo.update(run.id, status="completed", current_stage="completed", output=context, error="")
                await runner.project_repo.update(run.project_id, status="completed")
            except Exception as exc:
                await runner.run_repo.update(UUID(run_id), status="failed", error=str(exc))
                await runner.project_repo.update(run.project_id, status="failed")

    async def _persist_stage_output(self, run, name: str, context: dict[str, Any]):
        if name == "planning":
            await self.project_repo.update(run.project_id, world_setting=context.get("world_setting", {}))
            characters = context.get("characters", [])
            if characters and not await self.character_repo.get_by_project(run.project_id):
                await self.character_repo.batch_create([{**item, "project_id": run.project_id, "traits": item.get("traits", {})} for item in characters if item.get("name")])
        elif name == "writing" and context.get("script"):
            script = context["script"]
            await ScriptService(self.db).save_script(str(run.project_id), script.get("chapter_number", 1), script.get("title", ""), script.get("content", ""), script.get("scenes", []))
        elif name == "storyboarding" and context.get("storyboards"):
            script = await ScriptService(self.db).get_latest(str(run.project_id))
            if script:
                await ScriptService(self.db).save_storyboards(str(run.project_id), str(script.id), context["storyboards"])
