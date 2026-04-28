"""
User behavior tracking routes.

POST /api/behavior/          — record one event
GET  /api/behavior/{user_id} — query events for a user (with optional filters)
GET  /api/behavior/actions   — list all valid action values
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import UserAction, UserBehavior
from app.schemas import BehaviorEventRequest, BehaviorEventResponse, BehaviorListResponse

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _row_to_schema(row: UserBehavior) -> BehaviorEventResponse:
    return BehaviorEventResponse(
        id=row.id,
        user_id=row.user_id,
        action=row.action.value if isinstance(row.action, UserAction) else str(row.action),
        product_id=row.product_id,
        timestamp=row.timestamp.isoformat() if row.timestamp else "",
        metadata=row.metadata,
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get(
    "/actions",
    summary="List all valid action values",
    tags=["behavior"],
)
async def list_actions() -> dict:
    """Returns the complete set of trackable user action names."""
    return {"actions": [a.value for a in UserAction]}


@router.post(
    "/",
    response_model=BehaviorEventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a user behavior event",
    tags=["behavior"],
)
async def record_behavior(
    payload: BehaviorEventRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Persist a single user interaction event.

    - **action** must be one of the values from `GET /api/behavior/actions`.
    - **product_id** is optional for non-product actions (e.g. `search`, `view_category`).
    - **timestamp** is optional ISO-8601 string; defaults to current UTC time.
    - **metadata** is an optional free-form string (e.g. serialised JSON with
      `search_query`, `category_id`, `session_id`, etc.).
    """
    # Validate action enum
    try:
        action = UserAction(payload.action)
    except ValueError:
        valid = [a.value for a in UserAction]
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid action '{payload.action}'. Must be one of: {valid}",
        )

    # Parse optional client-provided timestamp
    ts: Optional[datetime] = None
    if payload.timestamp:
        try:
            ts = datetime.fromisoformat(payload.timestamp)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid timestamp '{payload.timestamp}'. Expected ISO-8601 format.",
            )

    event = UserBehavior(
        user_id=payload.user_id,
        action=action,
        product_id=payload.product_id,
        metadata=payload.metadata,
        **({"timestamp": ts} if ts is not None else {}),
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)

    logger.info(
        "behavior event recorded: user=%s action=%s product=%s",
        event.user_id,
        event.action.value,
        event.product_id,
    )
    return _row_to_schema(event)


@router.get(
    "/{user_id}",
    response_model=BehaviorListResponse,
    summary="Query behavior events for a user",
    tags=["behavior"],
)
async def get_user_behaviors(
    user_id: int,
    action: Optional[str] = Query(None, description="Filter by action type"),
    product_id: Optional[int] = Query(None, description="Filter by product_id"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Return paginated behavior events for a given user, newest first."""
    # Validate optional action filter
    action_filter: Optional[UserAction] = None
    if action:
        try:
            action_filter = UserAction(action)
        except ValueError:
            valid = [a.value for a in UserAction]
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid action filter '{action}'. Must be one of: {valid}",
            )

    base_q = select(UserBehavior).where(UserBehavior.user_id == user_id)
    if action_filter is not None:
        base_q = base_q.where(UserBehavior.action == action_filter)
    if product_id is not None:
        base_q = base_q.where(UserBehavior.product_id == product_id)

    count_result = await db.execute(
        select(func.count()).select_from(base_q.subquery())
    )
    total: int = count_result.scalar_one()

    rows_result = await db.execute(
        base_q.order_by(UserBehavior.timestamp.desc()).limit(limit).offset(offset)
    )
    events = [_row_to_schema(r) for r in rows_result.scalars().all()]

    return BehaviorListResponse(total=total, events=events)
