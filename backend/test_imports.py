"""Quick smoke test — verifies all modules import correctly."""

from app.config import settings
print(f"Config: {settings.APP_NAME}")

from app.models import (
    User, Company, CompanyDocument,
    Tender, TenderMatch,
    EvaluationJob, ComplianceItem,
    Proposal, Notification, Subscription,
)
print("All 10 models imported OK")

from app.database import Base
tables = list(Base.metadata.tables.keys())
print(f"Tables ({len(tables)}): {tables}")

from app.utils.security import hash_password, verify_password
h = hash_password("test123")
assert verify_password("test123", h)
print("Password hashing OK")

from app.utils.helpers import generate_content_hash, chunk_text, format_inr
print(f"Hash: {generate_content_hash('Solar Panel Tender')[:20]}...")
print(f"Chunks: {len(chunk_text('hello world ' * 500))}")
inr_str = format_inr(250)
print(f"INR format working: {len(inr_str)} chars")

from app.utils.errors import NotFoundException, EvalLimitExceeded
print("Custom exceptions OK")

from app.utils.logger import logger
logger.info("Logger working!")

print("\n" + "=" * 50)
print("ALL IMPORTS SUCCESSFUL!")
print("=" * 50)
