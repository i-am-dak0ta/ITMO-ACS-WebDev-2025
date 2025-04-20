from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from connection import get_session
from models import Users
from typing import List
from routers.auth import create_user_and_token
from schemas import UserCreate, UserRead, UserUpdate, UserWithToken

router = APIRouter(prefix = "/users", tags = ["Users"])


@router.post("/", response_model = UserWithToken)
def create_user(user_create: UserCreate, session: Session = Depends(get_session)):
    return create_user_and_token(user_create, session)


@router.get("/", response_model = List[UserRead])
def read_users(session: Session = Depends(get_session)):
    users = session.exec(select(Users)).all()
    return users


@router.get("/{user_id}", response_model = UserRead)
def read_user(user_id: int, session: Session = Depends(get_session)):
    user = session.get(Users, user_id)
    if not user:
        raise HTTPException(status_code = 404, detail = "User not found")
    return user


@router.patch("/{user_id}", response_model = UserRead)
def update_user(user_id: int, user_update: UserUpdate, session: Session = Depends(get_session)):
    user = session.get(Users, user_id)
    if not user:
        raise HTTPException(status_code = 404, detail = "User not found")
    user_data = user_update.dict(exclude_unset = True)
    for key, value in user_data.items():
        setattr(user, key, value)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@router.delete("/{user_id}")
def delete_user(user_id: int, session: Session = Depends(get_session)):
    user = session.get(Users, user_id)
    if not user:
        raise HTTPException(status_code = 404, detail = "User not found")
    session.delete(user)
    session.commit()
    return {"message": "User deleted successfully"}
