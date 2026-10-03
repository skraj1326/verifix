"""Subscription & Billing API endpoints."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select

router = APIRouter(prefix="/billing", tags=["Subscription & Billing"])


class PlanResponse(BaseModel):
    id: str
    name: str
    tier: str
    description: str
    price_monthly: int
    price_yearly: int
    features: List[str]
    limits: Dict[str, Any]
    is_active: bool


class SubscriptionResponse(BaseModel):
    id: str
    project_id: str
    plan_id: str
    plan_name: str
    tier: str
    status: str
    billing_interval: str
    current_period_start: str
    current_period_end: str
    trial_end: Optional[str]
    cancel_at_period_end: bool
    canceled_at: Optional[str]


class CreateSubscriptionRequest(BaseModel):
    project_id: str
    plan_id: str
    billing_interval: str = "monthly"  # monthly or yearly
    payment_method_id: Optional[str] = None


class UpdateSubscriptionRequest(BaseModel):
    plan_id: Optional[str] = None
    billing_interval: Optional[str] = None
    cancel_at_period_end: Optional[bool] = None


class CheckoutSessionRequest(BaseModel):
    plan_id: str
    billing_interval: str = "monthly"
    success_url: str
    cancel_url: str


class PortalSessionRequest(BaseModel):
    return_url: str


# Stripe configuration
STRIPE_SECRET_KEY = None
STRIPE_WEBHOOK_SECRET = None

try:
    import stripe
    import os
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
    if STRIPE_SECRET_KEY:
        stripe.api_key = STRIPE_SECRET_KEY
except ImportError:
    stripe = None


def get_stripe():
    if not stripe or not STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=503,
            detail="Stripe not configured. Set STRIPE_SECRET_KEY environment variable."
        )
    return stripe


# Plan endpoints
@router.get("/plans", response_model=List[PlanResponse])
async def list_plans():
    """List all available subscription plans."""
    from app.core.database import AsyncSessionLocal
    from app.models.database import Plan as PlanModel

    async with AsyncSessionLocal() as db:
        plans = (await db.execute(select(PlanModel).where(PlanModel.is_active == True))).scalars().all()

    return [
        PlanResponse(
            id=str(p.id),
            name=p.name,
            tier=p.tier.value,
            description=p.description,
            price_monthly=p.price_monthly,
            price_yearly=p.price_yearly,
            features=p.features,
            limits=p.limits,
            is_active=p.is_active,
        )
        for p in plans
    ]


@router.get("/plans/{plan_id}", response_model=PlanResponse)
async def get_plan(plan_id: str):
    """Get a specific plan by ID."""
    from app.core.database import AsyncSessionLocal
    from app.models.database import Plan as PlanModel
    from uuid import UUID

    try:
        plan_uuid = UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan ID format")

    async with AsyncSessionLocal() as db:
        plan = (await db.execute(select(PlanModel).where(PlanModel.id == plan_uuid))).scalar_one_or_none()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

    return PlanResponse(
        id=str(plan.id),
        name=plan.name,
        tier=plan.tier.value,
        description=plan.description,
        price_monthly=plan.price_monthly,
        price_yearly=plan.price_yearly,
        features=plan.features,
        limits=plan.limits,
        is_active=plan.is_active,
    )


# Subscription endpoints
@router.get("/subscription/{project_id}", response_model=SubscriptionResponse)
async def get_subscription(project_id: str):
    """Get the subscription for a project."""
    from app.core.database import AsyncSessionLocal
    from app.models.database import Subscription as SubscriptionModel, Plan as PlanModel
    from uuid import UUID

    try:
        project_uuid = UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")

    async with AsyncSessionLocal() as db:
        sub = (await db.execute(
            select(SubscriptionModel).where(SubscriptionModel.project_id == project_uuid)
        )).scalar_one_or_none()

        if not sub:
            raise HTTPException(status_code=404, detail="No subscription found for this project")

        plan = (await db.execute(select(PlanModel).where(PlanModel.id == sub.plan_id))).scalar_one_or_none()

    return SubscriptionResponse(
        id=str(sub.id),
        project_id=str(sub.project_id),
        plan_id=str(sub.plan_id),
        plan_name=plan.name if plan else "Unknown",
        tier=plan.tier.value if plan else "unknown",
        status=sub.status.value,
        billing_interval=sub.billing_interval.value,
        current_period_start=sub.current_period_start.isoformat(),
        current_period_end=sub.current_period_end.isoformat(),
        trial_end=sub.trial_end.isoformat() if sub.trial_end else None,
        cancel_at_period_end=sub.cancel_at_period_end,
        canceled_at=sub.canceled_at.isoformat() if sub.canceled_at else None,
    )


@router.post("/subscription", response_model=SubscriptionResponse)
async def create_subscription(request: CreateSubscriptionRequest):
    """Create a new subscription for a project."""
    from app.core.database import AsyncSessionLocal
    from app.models.database import Subscription as SubscriptionModel, Plan as PlanModel, Project as ProjectModel
    from uuid import UUID

    try:
        project_uuid = UUID(request.project_id)
        plan_uuid = UUID(request.plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    async with AsyncSessionLocal() as db:
        # Check project exists
        project = (await db.execute(select(ProjectModel).where(ProjectModel.id == project_uuid))).scalar_one_or_none()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Check plan exists
        plan = (await db.execute(select(PlanModel).where(PlanModel.id == plan_uuid))).scalar_one_or_none()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        # Check if project already has a subscription
        existing = (await db.execute(
            select(SubscriptionModel).where(SubscriptionModel.project_id == project_uuid)
        )).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="Project already has a subscription")

        # Get Stripe price ID based on billing interval
        stripe_price_id = plan.stripe_price_id_monthly if request.billing_interval == "monthly" else plan.stripe_price_id_yearly
        if not stripe_price_id:
            raise HTTPException(status_code=400, detail="Stripe price ID not configured for this plan/interval")

        # Create Stripe customer if needed
        stripe_client = get_stripe()
        customer = None
        if project.settings and project.settings.get("stripe_customer_id"):
            customer = stripe_client.Customer.retrieve(project.settings["stripe_customer_id"])
        else:
            customer = stripe_client.Customer.create(
                email=project.settings.get("email", "billing@verifix.ai"),
                metadata={"project_id": str(project.id)},
            )
            # Update project settings with customer ID
            project.settings = {**(project.settings or {}), "stripe_customer_id": customer.id}

        # Attach payment method if provided
        if request.payment_method_id:
            stripe_client.PaymentMethod.attach(
                request.payment_method_id,
                customer=customer.id,
            )
            stripe_client.Customer.modify(
                customer.id,
                invoice_settings={"default_payment_method": request.payment_method_id},
            )

        # Create Stripe subscription
        stripe_sub = stripe_client.Subscription.create(
            customer=customer.id,
            items=[{"price": stripe_price_id}],
            payment_behavior="default_incomplete",
            payment_settings={"save_default_payment_method": "on_subscription"},
            expand=["latest_invoice.payment_intent"],
            metadata={"project_id": str(project.id)},
        )

        # Determine billing interval
        billing_interval = "monthly" if request.billing_interval == "monthly" else "yearly"

        # Create local subscription record
        now = datetime.utcnow()
        sub = SubscriptionModel(
            project_id=project_uuid,
            plan_id=plan_uuid,
            status=stripe_sub.status,
            billing_interval=billing_interval,
            current_period_start=datetime.fromtimestamp(stripe_sub.current_period_start),
            current_period_end=datetime.fromtimestamp(stripe_sub.current_period_end),
            trial_start=datetime.fromtimestamp(stripe_sub.trial_start) if stripe_sub.trial_start else None,
            trial_end=datetime.fromtimestamp(stripe_sub.trial_end) if stripe_sub.trial_end else None,
            cancel_at_period_end=stripe_sub.cancel_at_period_end,
            stripe_customer_id=customer.id,
            stripe_subscription_id=stripe_sub.id,
            stripe_price_id=stripe_price_id,
        )
        db.add(sub)
        await db.commit()
        await db.refresh(sub)

    return SubscriptionResponse(
        id=str(sub.id),
        project_id=str(sub.project_id),
        plan_id=str(sub.plan_id),
        plan_name=plan.name,
        tier=plan.tier.value,
        status=sub.status.value,
        billing_interval=sub.billing_interval.value,
        current_period_start=sub.current_period_start.isoformat(),
        current_period_end=sub.current_period_end.isoformat(),
        trial_end=sub.trial_end.isoformat() if sub.trial_end else None,
        cancel_at_period_end=sub.cancel_at_period_end,
        canceled_at=sub.canceled_at.isoformat() if sub.canceled_at else None,
    )


@router.patch("/subscription/{project_id}", response_model=SubscriptionResponse)
async def update_subscription(project_id: str, request: UpdateSubscriptionRequest):
    """Update a subscription (change plan, billing interval, cancel at period end)."""
    from app.core.database import AsyncSessionLocal
    from app.models.database import Subscription as SubscriptionModel, Plan as PlanModel
    from uuid import UUID

    try:
        project_uuid = UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")

    async with AsyncSessionLocal() as db:
        sub = (await db.execute(
            select(SubscriptionModel).where(SubscriptionModel.project_id == project_uuid)
        )).scalar_one_or_none()

        if not sub:
            raise HTTPException(status_code=404, detail="No subscription found for this project")

        stripe_client = get_stripe()

        # Handle plan change
        if request.plan_id and request.plan_id != str(sub.plan_id):
            try:
                new_plan_uuid = UUID(request.plan_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid plan ID format")

            new_plan = (await db.execute(select(PlanModel).where(PlanModel.id == new_plan_uuid))).scalar_one_or_none()
            if not new_plan:
                raise HTTPException(status_code=404, detail="Plan not found")

            # Get new Stripe price ID
            new_price_id = new_plan.stripe_price_id_monthly if sub.billing_interval.value == "monthly" else new_plan.stripe_price_id_yearly
            if not new_price_id:
                raise HTTPException(status_code=400, detail="Stripe price ID not configured for new plan")

            # Update Stripe subscription
            stripe_client.Subscription.modify(
                sub.stripe_subscription_id,
                items=[{
                    "id": stripe_client.Subscription.retrieve(sub.stripe_subscription_id).items.data[0].id,
                    "price": new_price_id,
                }],
                proration_behavior="create_prorations",
            )

            sub.plan_id = new_plan_uuid
            sub.stripe_price_id = new_price_id

        # Handle billing interval change
        if request.billing_interval and request.billing_interval != sub.billing_interval.value:
            # This requires changing the Stripe subscription price
            plan = (await db.execute(select(PlanModel).where(PlanModel.id == sub.plan_id))).scalar_one_or_none()
            if not plan:
                raise HTTPException(status_code=404, detail="Plan not found")

            new_price_id = plan.stripe_price_id_monthly if request.billing_interval == "monthly" else plan.stripe_price_id_yearly
            if not new_price_id:
                raise HTTPException(status_code=400, detail="Stripe price ID not configured for this interval")

            stripe_client.Subscription.modify(
                sub.stripe_subscription_id,
                items=[{
                    "id": stripe_client.Subscription.retrieve(sub.stripe_subscription_id).items.data[0].id,
                    "price": new_price_id,
                }],
                proration_behavior="create_prorations",
            )

            sub.billing_interval = request.billing_interval
            sub.stripe_price_id = new_price_id

        # Handle cancel at period end
        if request.cancel_at_period_end is not None:
            stripe_client.Subscription.modify(
                sub.stripe_subscription_id,
                cancel_at_period_end=request.cancel_at_period_end,
            )
            sub.cancel_at_period_end = request.cancel_at_period_end

        await db.commit()
        await db.refresh(sub)

        plan = (await db.execute(select(PlanModel).where(PlanModel.id == sub.plan_id))).scalar_one_or_none()

    return SubscriptionResponse(
        id=str(sub.id),
        project_id=str(sub.project_id),
        plan_id=str(sub.plan_id),
        plan_name=plan.name if plan else "Unknown",
        tier=plan.tier.value if plan else "unknown",
        status=sub.status.value,
        billing_interval=sub.billing_interval.value,
        current_period_start=sub.current_period_start.isoformat(),
        current_period_end=sub.current_period_end.isoformat(),
        trial_end=sub.trial_end.isoformat() if sub.trial_end else None,
        cancel_at_period_end=sub.cancel_at_period_end,
        canceled_at=sub.canceled_at.isoformat() if sub.canceled_at else None,
    )


@router.post("/subscription/{project_id}/cancel")
async def cancel_subscription(project_id: str, immediately: bool = False):
    """Cancel a subscription."""
    from app.core.database import AsyncSessionLocal
    from app.models.database import Subscription as SubscriptionModel
    from uuid import UUID

    try:
        project_uuid = UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project ID format")

    async with AsyncSessionLocal() as db:
        sub = (await db.execute(
            select(SubscriptionModel).where(SubscriptionModel.project_id == project_uuid)
        )).scalar_one_or_none()

        if not sub:
            raise HTTPException(status_code=404, detail="No subscription found for this project")

        stripe_client = get_stripe()

        if immediately:
            stripe_client.Subscription.delete(sub.stripe_subscription_id)
            sub.status = "canceled"
            sub.canceled_at = datetime.utcnow()
        else:
            stripe_client.Subscription.modify(
                sub.stripe_subscription_id,
                cancel_at_period_end=True,
            )
            sub.cancel_at_period_end = True

        await db.commit()

    return {"message": "Subscription canceled" if immediately else "Subscription will cancel at period end"}


@router.post("/checkout-session")
async def create_checkout_session(request: CheckoutSessionRequest):
    """Create a Stripe Checkout session for subscription signup."""
    from app.core.database import AsyncSessionLocal
    from app.models.database import Plan as PlanModel
    from uuid import UUID

    try:
        plan_uuid = UUID(request.plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan ID format")

    async with AsyncSessionLocal() as db:
        plan = (await db.execute(select(PlanModel).where(PlanModel.id == plan_uuid))).scalar_one_or_none()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

    stripe_client = get_stripe()
    price_id = plan.stripe_price_id_monthly if request.billing_interval == "monthly" else plan.stripe_price_id_yearly
    if not price_id:
        raise HTTPException(status_code=400, detail="Stripe price ID not configured for this plan/interval")

    session = stripe_client.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=request.success_url,
        cancel_url=request.cancel_url,
        metadata={"plan_id": str(plan.id)},
    )

    return {"checkout_url": session.url, "session_id": session.id}


@router.post("/portal-session")
async def create_portal_session(request: PortalSessionRequest):
    """Create a Stripe Customer Portal session for subscription management."""
    from app.core.database import AsyncSessionLocal
    from app.models.database import Project as ProjectModel
    from uuid import UUID

    # In a real implementation, get the project_id from auth context
    # For now, require it in the request
    raise HTTPException(status_code=501, detail="Portal session requires authenticated project context")


# Stripe Webhook
@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events."""
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Stripe webhook secret not configured")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    stripe_client = get_stripe()

    try:
        event = stripe_client.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle the event
    from app.core.database import AsyncSessionLocal
    from app.models.database import Subscription as SubscriptionModel, Invoice as InvoiceModel

    async with AsyncSessionLocal() as db:
        if event.type == "customer.subscription.created":
            sub_data = event.data.object
            await _sync_subscription_from_stripe(db, sub_data)

        elif event.type == "customer.subscription.updated":
            sub_data = event.data.object
            await _sync_subscription_from_stripe(db, sub_data)

        elif event.type == "customer.subscription.deleted":
            sub_data = event.data.object
            await _handle_subscription_deleted(db, sub_data)

        elif event.type == "invoice.payment_succeeded":
            invoice_data = event.data.object
            await _sync_invoice_from_stripe(db, invoice_data)

        elif event.type == "invoice.payment_failed":
            invoice_data = event.data.object
            await _sync_invoice_from_stripe(db, invoice_data)

        await db.commit()

    return {"received": True}


async def _sync_subscription_from_stripe(db, stripe_sub):
    """Sync subscription data from Stripe to local database."""
    from app.models.database import Subscription as SubscriptionModel
    from uuid import UUID

    local_sub = (await db.execute(
        select(SubscriptionModel).where(SubscriptionModel.stripe_subscription_id == stripe_sub.id)
    )).scalar_one_or_none()

    if local_sub:
        local_sub.status = stripe_sub.status
        local_sub.current_period_start = datetime.fromtimestamp(stripe_sub.current_period_start)
        local_sub.current_period_end = datetime.fromtimestamp(stripe_sub.current_period_end)
        local_sub.cancel_at_period_end = stripe_sub.cancel_at_period_end
        local_sub.canceled_at = datetime.fromtimestamp(stripe_sub.canceled_at) if stripe_sub.canceled_at else None
        local_sub.trial_start = datetime.fromtimestamp(stripe_sub.trial_start) if stripe_sub.trial_start else None
        local_sub.trial_end = datetime.fromtimestamp(stripe_sub.trial_end) if stripe_sub.trial_end else None


async def _handle_subscription_deleted(db, stripe_sub):
    """Handle subscription deletion."""
    from app.models.database import Subscription as SubscriptionModel

    local_sub = (await db.execute(
        select(SubscriptionModel).where(SubscriptionModel.stripe_subscription_id == stripe_sub.id)
    )).scalar_one_or_none()

    if local_sub:
        local_sub.status = "canceled"
        local_sub.canceled_at = datetime.utcnow()


async def _sync_invoice_from_stripe(db, stripe_invoice):
    """Sync invoice data from Stripe to local database."""
    from app.models.database import Invoice as InvoiceModel, Subscription as SubscriptionModel

    # Find local subscription
    local_sub = (await db.execute(
        select(SubscriptionModel).where(SubscriptionModel.stripe_customer_id == stripe_invoice.customer)
    )).scalar_one_or_none()

    if not local_sub:
        return

    # Check if invoice exists
    existing = (await db.execute(
        select(InvoiceModel).where(InvoiceModel.stripe_invoice_id == stripe_invoice.id)
    )).scalar_one_or_none()

    if existing:
        existing.status = stripe_invoice.status
        existing.amount_paid = stripe_invoice.amount_paid
        existing.amount_remaining = stripe_invoice.amount_remaining
        existing.paid_at = datetime.fromtimestamp(stripe_invoice.status_transitions.paid_at) if stripe_invoice.status_transitions.paid_at else None
    else:
        invoice = InvoiceModel(
            subscription_id=local_sub.id,
            stripe_invoice_id=stripe_invoice.id,
            amount_due=stripe_invoice.amount_due,
            amount_paid=stripe_invoice.amount_paid,
            amount_remaining=stripe_invoice.amount_remaining,
            currency=stripe_invoice.currency,
            status=stripe_invoice.status,
            invoice_pdf=stripe_invoice.invoice_pdf,
            hosted_invoice_url=stripe_invoice.hosted_invoice_url,
            period_start=datetime.fromtimestamp(stripe_invoice.period_start),
            period_end=datetime.fromtimestamp(stripe_invoice.period_end),
            due_date=datetime.fromtimestamp(stripe_invoice.due_date) if stripe_invoice.due_date else None,
            paid_at=datetime.fromtimestamp(stripe_invoice.status_transitions.paid_at) if stripe_invoice.status_transitions.paid_at else None,
        )
        db.add(invoice)