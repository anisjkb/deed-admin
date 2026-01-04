# src/backend/crud/feedback.py
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, desc, update
from sqlalchemy.exc import IntegrityError

from src.backend.models.ops.feedback import Feedback
from src.backend.schemas.feedback_schema import FeedbackCreate, FeedbackUpdate


# -------- Get one feedback --------
async def get_feedback(db: AsyncSession, feedback_id: int) -> Optional[Feedback]:
    stmt = select(Feedback).where(Feedback.id == feedback_id)
    res = await db.execute(stmt)
    return res.scalar_one_or_none()


# -------- List feedback (search + pagination) --------
async def list_feedback(
    db: AsyncSession,
    q: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> List[Feedback]:
    stmt = select(Feedback).order_by(Feedback.id.asc())
    if q:
        ilike = f"%{q}%"
        stmt = stmt.where(
            (Feedback.name.ilike(ilike)) |
            (Feedback.email.ilike(ilike)) |
            (Feedback.message.ilike(ilike)) |
            (Feedback.phone.ilike(ilike))
        )
    res = await db.execute(stmt.limit(limit).offset(offset))
    return list(res.scalars().all())


# -------- Count feedback (for pagination) --------
async def get_total_feedback_count(db: AsyncSession, q: Optional[str] = None) -> int:
    stmt = select(func.count(Feedback.id))
    if q:
        ilike = f"%{q}%"
        stmt = stmt.where(
            (Feedback.name.ilike(ilike)) |
            (Feedback.email.ilike(ilike)) |
            (Feedback.message.ilike(ilike)) |
            (Feedback.phone.ilike(ilike))
        )
    res = await db.execute(stmt)
    return int(res.scalar_one() or 0)


# -------- Create feedback --------
async def create_feedback(
    db: AsyncSession,
    payload: FeedbackCreate,
    created_by: str = "System",
) -> Feedback:
    row = Feedback(
        name=payload.name,
        phone=payload.phone,
        email=payload.email,
        message=payload.message,
    )
    db.add(row)
    try:
        await db.commit()
        await db.refresh(row)
    except IntegrityError:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise
    return row


# -------- Update feedback (admin only; optional) --------
async def update_feedback(
    db: AsyncSession,
    feedback_id: int,
    payload: FeedbackUpdate,
    updated_by: str = "System",
) -> Optional[Feedback]:
    row = await get_feedback(db, feedback_id)
    if not row:
        return None

    row.name = payload.name
    row.phone = payload.phone
    row.email = payload.email
    row.message = payload.message

    try:
        await db.commit()
        await db.refresh(row)
    except IntegrityError:
        await db.rollback()
        raise
    return row


# -------- Delete feedback --------
async def delete_feedback(db: AsyncSession, feedback_id: int) -> bool:
    stmt = delete(Feedback).where(Feedback.id == feedback_id)
    res = await db.execute(stmt)
    await db.commit()
    return res.rowcount > 0


# ============================================================
# 📩 UNREAD HELPERS & MARK-AS-READ SUPPORT
# ============================================================

# -------- List unread feedback (latest first, limited) --------
async def list_unread_feedback(db: AsyncSession, limit: int = 10) -> List[Feedback]:
    """
    Return the latest unread feedback (default: 10 newest).
    Used for the notification bell dropdown.
    """
    stmt = (
        select(Feedback)
        .where(Feedback.is_read.is_(False))
        .order_by(Feedback.created_at.desc())
        .limit(limit)
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())


# -------- Count unread feedback (for dynamic badge) --------
async def count_unread_feedback(db: AsyncSession) -> int:
    stmt = select(func.count(Feedback.id)).where(Feedback.is_read.is_(False))
    res = await db.execute(stmt)
    return int(res.scalar_one() or 0)


# -------- Mark feedback as read --------
async def mark_feedback_read(db: AsyncSession, feedback_id: int) -> bool:
    """
    Marks a feedback row as read when user views it.
    Returns True if an unread record was updated.
    """
    stmt = (
        update(Feedback)
        .where(Feedback.id == feedback_id, Feedback.is_read.is_(False))
        .values(is_read=True)
    )
    res = await db.execute(stmt)
    await db.commit()
    return res.rowcount > 0