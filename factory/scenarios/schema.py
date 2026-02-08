"""Pydantic v2 models for factory test scenarios."""

from enum import Enum
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel


class ScenarioPriority(str, Enum):
    critical = 'critical'
    high = 'high'
    medium = 'medium'
    low = 'low'


class ScenarioType(str, Enum):
    visual_quality = 'visual_quality'
    performance = 'performance'
    comparative = 'comparative'
    regression = 'regression'


class MetricAssertion(BaseModel):
    model_config = {'frozen': False}

    metric: str
    operator: Literal['>=', '<=', '==', '>', '<', '!=']
    value: float


class LLMJudgeConfig(BaseModel):
    model_config = {'frozen': False}

    enabled: bool = False
    model: str = 'claude-sonnet-4-20250514'
    min_samples: int = 3
    dimensions: Dict[str, float] = {}


class SetupConfig(BaseModel):
    model_config = {'frozen': False}

    source_profile: Optional[str] = None
    source_image: Optional[str] = None
    target_image: Optional[str] = None
    target_video: Optional[str] = None
    preset: Optional[str] = None
    lora_model: Optional[str] = None


class Assertions(BaseModel):
    model_config = {'frozen': False}

    metrics: List[MetricAssertion] = []
    llm_judge: Optional[LLMJudgeConfig] = None
    performance: Dict[str, float] = {}
    golden_ref: Optional[str] = None


class Scenario(BaseModel):
    model_config = {'frozen': False}

    name: str
    description: str
    type: ScenarioType
    priority: ScenarioPriority
    setup: SetupConfig
    assertions: Assertions
    tags: List[str] = []
