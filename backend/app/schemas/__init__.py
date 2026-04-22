# app/shemas/__init__.py

"""
Schemas Pydantic
Export tous les schemas pour validation API
"""

# User schemas
from .user import (
    UserCreate,
    UserUpdate,
    UserLogin,
    UserResponse,
    UserWithStats,
    PasswordChange,
    Token,
    TokenData
)

# Signalement schemas
from .signalement import (
    SignalementCreate,
    SignalementUpdate,
    SignalementResponse,
    SignalementDetail,
    SignalementList
)

# Estimation schemas
from .estimation import (
    EstimationCreate,
    EstimationRequest,
    EstimationResponse,
    EstimationDetail,
    EstimationComparison
)

# Scenario schemas
from .scenario import (
    ScenarioType,
    CostItem,
    ScenarioAction,
    Scenario,
)

__all__ = [
    # User
    "UserCreate",
    "UserUpdate",
    "UserLogin",
    "UserResponse",
    "UserWithStats",
    "PasswordChange",
    "Token",
    "TokenData",
    # Signalement
    "SignalementCreate",
    "SignalementUpdate",
    "SignalementResponse",
    "SignalementDetail",
    "SignalementList",
    # Estimation
    "EstimationCreate",
    "EstimationRequest",
    "EstimationResponse",
    "EstimationDetail",
    "EstimationComparison",
    # Scenario
    "ScenarioType",
    "CostItem",
    "ScenarioAction",
    "Scenario",
]
