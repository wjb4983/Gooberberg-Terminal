from fastapi import Request

from app.domain.job_runner import JobRunnerService
from app.domain.model_configs import ModelConfigService
from app.domain.model_registry import ModelRegistry
from app.domain.task_registry import TaskRegistry


def get_model_registry(request: Request) -> ModelRegistry:
    return request.app.state.model_registry


def get_task_registry(request: Request) -> TaskRegistry:
    return request.app.state.task_registry


def get_job_runner_service(request: Request) -> JobRunnerService:
    return request.app.state.job_runner_service


def get_model_config_service(request: Request) -> ModelConfigService:
    return request.app.state.model_config_service
