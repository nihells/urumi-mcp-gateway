from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import MCPServer, User
from app.routers.auth import get_current_user

router = APIRouter(prefix="/servers", tags=["MCP Servers"])


class ServerCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    url: str = Field(min_length=8, max_length=500)
    description: str = Field(default="", max_length=500)


class ServerUpdate(BaseModel):
    url: str | None = Field(default=None, min_length=8, max_length=500)
    description: str | None = Field(default=None, max_length=500)
    enabled: bool | None = None


def require_admin(user: User):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access required.")


def validate_server_url(url: str):
    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(
            status_code=422,
            detail="Server URL must be a valid HTTP or HTTPS URL.",
        )

    if parsed.username or parsed.password:
        raise HTTPException(
            status_code=422,
            detail="Do not embed credentials in the server URL.",
        )


@router.get("")
def list_servers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    servers = db.query(MCPServer).order_by(MCPServer.id).all()

    return [
        {
            "id": server.id,
            "name": server.name,
            "url": server.url,
            "description": server.description,
            "enabled": server.enabled,
        }
        for server in servers
    ]


@router.post("")
def create_server(
    data: ServerCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_admin(current_user)
    validate_server_url(data.url)

    if db.query(MCPServer).filter(MCPServer.name == data.name).first():
        raise HTTPException(status_code=409, detail="Server name already exists.")

    server = MCPServer(
        name=data.name,
        url=data.url.rstrip("/"),
        description=data.description,
        enabled=True,
    )

    db.add(server)
    db.commit()
    db.refresh(server)

    return {
        "id": server.id,
        "name": server.name,
        "url": server.url,
        "enabled": server.enabled,
    }


@router.patch("/{server_id}")
def update_server(
    server_id: int,
    data: ServerUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_admin(current_user)

    server = db.get(MCPServer, server_id)

    if not server:
        raise HTTPException(status_code=404, detail="Server not found.")

    changes = data.model_dump(exclude_unset=True)

    if "url" in changes and changes["url"] is not None:
        validate_server_url(changes["url"])
        server.url = changes["url"].rstrip("/")

    if "description" in changes and changes["description"] is not None:
        server.description = changes["description"]

    if "enabled" in changes and changes["enabled"] is not None:
        server.enabled = changes["enabled"]

    db.commit()
    db.refresh(server)

    return {
        "id": server.id,
        "name": server.name,
        "url": server.url,
        "description": server.description,
        "enabled": server.enabled,
    }


@router.delete("/{server_id}")
def delete_server(
    server_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_admin(current_user)

    server = db.get(MCPServer, server_id)

    if not server:
        raise HTTPException(status_code=404, detail="Server not found.")

    db.delete(server)
    db.commit()

    return {"message": "Server deleted.", "id": server_id}