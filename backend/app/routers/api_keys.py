from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ApiKey, User
from app.routers.auth import get_current_user
from app.security import api_key_prefix, generate_api_key, hash_api_key

router = APIRouter(prefix="/api-keys", tags=["API Keys"])


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


@router.post("")
def create_api_key(
    data: ApiKeyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    raw_key = generate_api_key()

    record = ApiKey(
        user_id=current_user.id,
        name=data.name.strip(),
        key_prefix=api_key_prefix(raw_key),
        key_hash=hash_api_key(raw_key),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "id": record.id,
        "name": record.name,
        "api_key": raw_key,
        "key_prefix": record.key_prefix,
        "created_at": record.created_at,
        "warning": "Copy this key now. It will not be shown again.",
    }


@router.get("")
def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(ApiKey)

    if current_user.role != "admin":
        query = query.filter(ApiKey.user_id == current_user.id)

    return [
        {
            "id": key.id,
            "user_id": key.user_id,
            "name": key.name,
            "key_prefix": key.key_prefix,
            "revoked": key.revoked,
            "created_at": key.created_at,
            "revoked_at": key.revoked_at,
        }
        for key in query.order_by(ApiKey.id.desc()).all()
    ]


@router.delete("/{key_id}")
def revoke_api_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    key = db.get(ApiKey, key_id)

    if not key:
        raise HTTPException(status_code=404, detail="API key not found.")

    if current_user.role != "admin" and key.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied.")

    if not key.revoked:
        key.revoked = True
        key.revoked_at = datetime.now(timezone.utc)
        db.commit()

    return {"message": "API key revoked.", "id": key.id}
