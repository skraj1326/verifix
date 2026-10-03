"""Seed default subscription plans into the database."""

import asyncio
from uuid import uuid4

from sqlalchemy import select

from app.core.database import AsyncSessionLocal, init_db
from app.models.database import Plan, SubscriptionTier, BillingInterval


DEFAULT_PLANS = [
    {
        "name": "Free",
        "tier": SubscriptionTier.FREE,
        "description": "Perfect for individual developers and small projects",
        "price_monthly": 0,
        "price_yearly": 0,
        "features": [
            "Up to 3 projects",
            "Up to 10 simulations/month",
            "Basic coverage analysis",
            "VCD waveform viewer",
            "Community support",
        ],
        "limits": {
            "projects": 3,
            "simulations_per_month": 10,
            "storage_gb": 1,
            "team_members": 1,
            "api_calls_per_month": 1000,
        },
        "stripe_price_id_monthly": None,
        "stripe_price_id_yearly": None,
    },
    {
        "name": "Starter",
        "tier": SubscriptionTier.STARTER,
        "description": "Great for growing teams and small companies",
        "price_monthly": 4900,  # $49/month
        "price_yearly": 49000,  # $490/year (2 months free)
        "features": [
            "Up to 10 projects",
            "Unlimited simulations",
            "Advanced coverage analysis",
            "VCD & FST waveform viewer",
            "PDF report export",
            "Email support",
            "API access",
        ],
        "limits": {
            "projects": 10,
            "simulations_per_month": -1,  # unlimited
            "storage_gb": 10,
            "team_members": 5,
            "api_calls_per_month": 10000,
        },
        "stripe_price_id_monthly": "price_starter_monthly",
        "stripe_price_id_yearly": "price_starter_yearly",
    },
    {
        "name": "Professional",
        "tier": SubscriptionTier.PROFESSIONAL,
        "description": "For professional verification teams",
        "price_monthly": 19900,  # $199/month
        "price_yearly": 199000,  # $1990/year
        "features": [
            "Unlimited projects",
            "Unlimited simulations",
            "Full coverage dashboard",
            "Advanced waveform analysis",
            "Custom report templates",
            "Priority email support",
            "API access with higher limits",
            "SSO integration",
        ],
        "limits": {
            "projects": -1,  # unlimited
            "simulations_per_month": -1,
            "storage_gb": 100,
            "team_members": 20,
            "api_calls_per_month": 100000,
        },
        "stripe_price_id_monthly": "price_pro_monthly",
        "stripe_price_id_yearly": "price_pro_yearly",
    },
    {
        "name": "Enterprise",
        "tier": SubscriptionTier.ENTERPRISE,
        "description": "For large organizations with custom requirements",
        "price_monthly": 49900,  # $499/month
        "price_yearly": 499000,  # $4990/year
        "features": [
            "Unlimited everything",
            "Dedicated infrastructure options",
            "Custom SLAs",
            "On-premise deployment option",
            "24/7 phone support",
            "Custom integrations",
            "Audit logs",
            "Advanced security features",
        ],
        "limits": {
            "projects": -1,
            "simulations_per_month": -1,
            "storage_gb": -1,  # unlimited
            "team_members": -1,
            "api_calls_per_month": -1,
        },
        "stripe_price_id_monthly": "price_enterprise_monthly",
        "stripe_price_id_yearly": "price_enterprise_yearly",
    },
]


async def seed_plans():
    """Insert default plans if they don't exist."""
    await init_db()

    async with AsyncSessionLocal() as db:
        for plan_data in DEFAULT_PLANS:
            existing = (await db.execute(
                select(Plan).where(Plan.name == plan_data["name"])
            )).scalar_one_or_none()

            if not existing:
                plan = Plan(
                    id=uuid4(),
                    **plan_data,
                )
                db.add(plan)
                print(f"Created plan: {plan_data['name']}")
            else:
                print(f"Plan already exists: {plan_data['name']}")

        await db.commit()
        print("Seeding complete!")


if __name__ == "__main__":
    asyncio.run(seed_plans())