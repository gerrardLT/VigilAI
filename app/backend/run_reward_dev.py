from __future__ import annotations

import sys

import uvicorn

sys.path.insert(0, r"D:\5个项目\VigilAI\.worktrees\reward-opportunity-agent\app\backend")

from api import app
from data_manager import DataManager
from reward_opportunity.repository import RewardOpportunityRepository
from reward_opportunity.service import RewardOpportunityService
from scheduler import TaskScheduler


def main() -> None:
    data_manager = DataManager()
    scheduler = TaskScheduler(data_manager)
    app.state.data_manager = data_manager
    app.state.scheduler = scheduler
    app.state.reward_opportunity_repository = RewardOpportunityRepository(data_manager.db_path)
    app.state.reward_opportunity_service = RewardOpportunityService(app.state.reward_opportunity_repository)
    scheduler.reward_opportunity_service = app.state.reward_opportunity_service
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="info")


if __name__ == "__main__":
    main()
