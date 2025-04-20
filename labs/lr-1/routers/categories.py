from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from connection import get_session
from models import Categories
from schemas import CategoryRead
from typing import List

router = APIRouter(prefix = "/categories", tags = ["Categories"])


@router.get("/", response_model = List[CategoryRead])
def read_categories(
    session: Session = Depends(get_session)
):
    categories = session.exec(select(Categories)).all()
    return categories


@router.get("/{category_id}", response_model = CategoryRead)
def read_category(
    category_id: int,
    session: Session = Depends(get_session)
):
    category = session.get(Categories, category_id)
    if not category:
        raise HTTPException(status_code = 404, detail = "Category not found")
    return category
