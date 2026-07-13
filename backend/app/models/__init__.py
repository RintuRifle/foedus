"""
Foedus — SQLAlchemy ORM Models
Import all models here so Alembic can detect them.
"""

from app.models.user import User
from app.models.company import Company, CompanyDocument
from app.models.tender import Tender, TenderMatch
from app.models.evaluation import EvaluationJob, ComplianceItem
from app.models.proposal import Proposal
from app.models.notification import Notification, Subscription

__all__ = [
    "User",
    "Company",
    "CompanyDocument",
    "Tender",
    "TenderMatch",
    "EvaluationJob",
    "ComplianceItem",
    "Proposal",
    "Notification",
    "Subscription",
]
