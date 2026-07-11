import asyncio
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import async_session_factory
from app.models.tender import Tender

async def create_dummy_tender():
    async with async_session_factory() as db:
        tender_id = uuid.uuid4()
        tender = Tender(
            id=tender_id,
            external_id="DUMMY-TENDER-001",
            source="manual",
            title="Supply and Installation of 50kW Solar Power Plant",
            description="The government requires the supply, installation, testing and commissioning of a 50kW grid-connected rooftop solar power plant in Patna, Bihar.",
            sector=["solar", "renewable energy"],
            state="Bihar",
            department="Department of Energy",
            value_lakh=25.00,
            emd_amount=0.50,
            tender_fee=0.01,
            parsed_text="""
            NOTICE INVITING TENDER
            1. Name of Work: Supply, Installation, Testing and Commissioning of 50kW Grid Connected Rooftop Solar Power Plant.
            2. Estimated Cost: Rs. 25,00,000/-
            3. Earnest Money Deposit: Rs. 50,000/-
            4. Eligibility Criteria:
               a. The bidder must have an average annual turnover of minimum Rs. 50 Lakhs in the last 3 financial years.
               b. The bidder must have successfully installed at least one solar power plant of 20kW or above in the last 5 years.
               c. The bidder must possess a valid ISO 9001 certification.
               d. Must have registered office in Bihar.
               e. Valid PAN and GST registration.
            """,
            content_hash=str(uuid.uuid4()),
            status="active",
            scraped_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc)
        )
        db.add(tender)
        await db.commit()
        print(f"✅ Dummy tender created successfully! ID: {tender_id}")

if __name__ == "__main__":
    asyncio.run(create_dummy_tender())
