from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..api_schemas import ParentRequestCreate
from ..auth_dependencies import get_current_user, require_role
from ..business import parent_child_progress, parent_has_link, pending_requests_for_child
from ..db import get_db
from ..db_models import ParentChildLink, ParentLinkRequest, RequestStatus, User, UserRole

router = APIRouter(prefix="/api/v1/parent", tags=["parent"])


@router.post("/requests")
def create_parent_request(
    payload: ParentRequestCreate,
    db: Session = Depends(get_db),
    parent: User = Depends(require_role(UserRole.PARENT)),
) -> dict:
    child = db.scalar(select(User).where(User.username == payload.child_username, User.role == UserRole.STUDENT))
    if child is None:
        raise HTTPException(status_code=404, detail="Child not found")
    if parent_has_link(db, parent.id, child.id):
        raise HTTPException(status_code=409, detail="Already linked")

    pending = db.scalar(
        select(ParentLinkRequest).where(
            ParentLinkRequest.parent_id == parent.id,
            ParentLinkRequest.child_id == child.id,
            ParentLinkRequest.status == RequestStatus.PENDING,
        )
    )
    if pending:
        raise HTTPException(status_code=409, detail="Request already pending")

    req = ParentLinkRequest(parent_id=parent.id, child_id=child.id, status=RequestStatus.PENDING)
    db.add(req)
    db.commit()
    db.refresh(req)
    return {"ok": True, "request_id": req.id}


@router.get("/requests/incoming")
def incoming_parent_requests(
    db: Session = Depends(get_db),
    student: User = Depends(require_role(UserRole.STUDENT)),
) -> dict:
    requests = pending_requests_for_child(db, student.id)
    parent_map = {u.id: u.username for u in db.scalars(select(User).where(User.id.in_([r.parent_id for r in requests]))).all()} if requests else {}
    return {
        "items": [
            {
                "id": r.id,
                "parent_id": r.parent_id,
                "parent_username": parent_map.get(r.parent_id, "unknown"),
                "status": r.status.value,
                "created_at": r.created_at.isoformat(),
            }
            for r in requests
        ]
    }


@router.post("/requests/{request_id}/accept")
def accept_request(
    request_id: int,
    db: Session = Depends(get_db),
    student: User = Depends(require_role(UserRole.STUDENT)),
) -> dict:
    req = db.get(ParentLinkRequest, request_id)
    if req is None or req.child_id != student.id:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status != RequestStatus.PENDING:
        raise HTTPException(status_code=400, detail="Request already processed")

    req.status = RequestStatus.ACCEPTED
    req.responded_at = datetime.utcnow()
    if not parent_has_link(db, req.parent_id, req.child_id):
        db.add(ParentChildLink(parent_id=req.parent_id, child_id=req.child_id))
    db.commit()
    return {"ok": True}


@router.post("/requests/{request_id}/reject")
def reject_request(
    request_id: int,
    db: Session = Depends(get_db),
    student: User = Depends(require_role(UserRole.STUDENT)),
) -> dict:
    req = db.get(ParentLinkRequest, request_id)
    if req is None or req.child_id != student.id:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status != RequestStatus.PENDING:
        raise HTTPException(status_code=400, detail="Request already processed")

    req.status = RequestStatus.REJECTED
    req.responded_at = datetime.utcnow()
    db.commit()
    return {"ok": True}


@router.get("/children")
def list_children(
    db: Session = Depends(get_db),
    parent: User = Depends(require_role(UserRole.PARENT)),
) -> dict:
    links = db.scalars(select(ParentChildLink).where(ParentChildLink.parent_id == parent.id)).all()
    child_ids = [l.child_id for l in links]
    children = db.scalars(select(User).where(User.id.in_(child_ids))).all() if child_ids else []
    return {"items": [{"id": c.id, "username": c.username, "xp": c.xp, "level": c.level} for c in children]}


@router.get("/children/{child_id}/progress")
def child_progress(
    child_id: int,
    db: Session = Depends(get_db),
    parent: User = Depends(require_role(UserRole.PARENT)),
) -> dict:
    if not parent_has_link(db, parent.id, child_id):
        raise HTTPException(status_code=403, detail="No access to this child")
    child = db.get(User, child_id)
    if child is None or child.role != UserRole.STUDENT:
        raise HTTPException(status_code=404, detail="Child not found")
    return parent_child_progress(db, child)
