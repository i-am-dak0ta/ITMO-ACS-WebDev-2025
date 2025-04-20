from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from connection import get_session
from models import Tags
from schemas import TagRead
from typing import List

router = APIRouter(prefix = "/tags", tags = ["Tags"])


@router.get("/", response_model = List[TagRead])
def read_tags(
    session: Session = Depends(get_session)
):
    tags = session.exec(select(Tags)).all()
    return tags


@router.get("/{tag_id}", response_model = TagRead)
def read_tag(
    tag_id: int,
    session: Session = Depends(get_session)
):
    tag = session.get(Tags, tag_id)
    if not tag:
        raise HTTPException(status_code = 404, detail = "Tag not found")
    return tag
