import datetime
import os
import jwt
from fastapi import APIRouter, HTTPException, Depends, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session, select
from passlib.context import CryptContext
from connection import get_session
from models import Users
from schemas import UserCreate, UserRead, UserLogin, UserPassword, UserWithToken

router = APIRouter(prefix = "/auth", tags = ["Authentication"])

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes = ["bcrypt"], deprecated = "auto")
auth_scheme = HTTPBearer()


def create_access_token(data: dict, expires_delta: datetime.timedelta = None) -> str:
    payload = data.copy()
    if expires_delta:
        expire = datetime.datetime.now(datetime.timezone.utc) + expires_delta
    else:
        expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
            minutes = ACCESS_TOKEN_EXPIRE_MINUTES
        )
    payload.update({"exp": expire})
    encoded_jwt = jwt.encode(payload, SECRET_KEY, algorithm = ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms = [ALGORITHM])
        return payload.get("sub")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code = status.HTTP_401_UNAUTHORIZED, detail = "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code = status.HTTP_401_UNAUTHORIZED, detail = "Invalid token")


def create_user_with_hash(user_create: UserCreate, session: Session) -> Users:
    username_statement = select(Users).where(Users.username == user_create.username)
    existing_user = session.exec(username_statement).first()
    if existing_user:
        raise HTTPException(status_code = 400, detail = "Username already registered")

    email_statement = select(Users).where(Users.email == user_create.email)
    existing_email = session.exec(email_statement).first()
    if existing_email:
        raise HTTPException(status_code = 400, detail = "Email already registered")

    hashed_password = pwd_context.hash(user_create.password)

    new_user = Users(
        username = user_create.username,
        password = hashed_password,
        first_name = user_create.first_name,
        last_name = user_create.last_name,
        email = user_create.email
    )
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    return new_user


def create_user_and_token(user_create: UserCreate, session: Session) -> dict:
    user = create_user_with_hash(user_create, session)
    token = create_access_token(data = {"sub": user.username})
    return {
        "user": UserRead.model_validate(user),
        "access_token": token,
        "token_type": "bearer"
    }


@router.post("/register", response_model = UserWithToken)
def register(user_create: UserCreate, session: Session = Depends(get_session)):
    return create_user_and_token(user_create, session)


@router.post("/login", response_model = UserWithToken)
def login(user_login: UserLogin, session: Session = Depends(get_session)):
    statement = select(Users).where(Users.username == user_login.username)
    user = session.exec(statement).first()
    if not user or not pwd_context.verify(user_login.password, user.password):
        raise HTTPException(status_code = 401, detail = "Invalid credentials")
    token = create_access_token(data = {"sub": user.username})
    return {
        "user": UserRead.model_validate(user),
        "access_token": token,
        "token_type": "bearer"
    }


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(auth_scheme),
    session: Session = Depends(get_session)
) -> Users:
    token = credentials.credentials
    username = verify_token(token)
    statement = select(Users).where(Users.username == username)
    user = session.exec(statement).first()
    if not user: raise HTTPException(status_code = 404, detail = "User not found")
    return user


@router.get("/me", response_model = UserRead)
def read_current_user(current_user: Users = Depends(get_current_user)):
    return current_user


@router.patch("/change-password")
def change_password(
    pwd_data: UserPassword,
    current_user: Users = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    if not pwd_context.verify(pwd_data.old_password, current_user.password):
        raise HTTPException(status_code = 400, detail = "Incorrect current password")
    current_user.password = pwd_context.hash(pwd_data.new_password)
    session.add(current_user)
    session.commit()
    return {"message": "Password updated successfully"}
