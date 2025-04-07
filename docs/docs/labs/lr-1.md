# Лабораторная работа 1. Реализация серверного приложения FastAPI

## Цели

Научится реализовывать полноценное серверное приложение с помощью фреймворка FastAPI с применением дополнительных средств и библиотек.

## Практическая часть

### Описание приложения на тему "Разработка сервиса для управления личными финансами"

#### Структура базы данных

![Схема БД](../assets/lr-1/DB_Schema.jpg)

Модель данных включает 8 таблиц:
1. Users - пользователи.
2. TransactionTypes - типы транзакций.
3. Categories - категории транзакций.
4. Budgets - бюджеты пользователей.
5. Goals - финансовые цели.
6. Notifications - уведомления.
7. Tags - теги для транзакций.
8. Transactions - транзакции.

Связи:
- One-to-Many: `Users` → `Transactions`, `Users` → `Budgets`, `Users` → `Goals`, `Users` → `Notifications`.
- Many-to-Many: `Transactions` ↔ `Tags` через ассоциативную таблицу `TransactionTags`.
- Ассоциативная сущность: `TransactionTags` содержит поле `transaction_tag_id` помимо внешних ключей, что соответствует требованиям задания.

### Реализация кода

#### Подключение к базе данных (`connection.py`)
Файл настраивает подключение к базе данных и инициализирует таблицы:

```python
import os  
from dotenv import load_dotenv  
from sqlmodel import SQLModel, Session, create_engine  

load_dotenv()  
db_url = os.getenv("DB_ADMIN")  
engine = create_engine(db_url, echo=True)  

def init_db():  
    SQLModel.metadata.create_all(engine)  

def get_session():  
    with Session(engine) as session:  
        yield session
```

#### Главный файл приложения (`main.py`)
Создаёт приложение FastAPI, подключает маршруты и инициализирует базу данных при запуске:

```python
from fastapi import FastAPI  
from connection import init_db  
from routers import auth, users  

app = FastAPI()  

@app.on_event("startup")  
def on_startup():  
    init_db()  

app.include_router(users.router)  
app.include_router(auth.router)  

@app.get("/")  
def hello():  
    return "Hello, Artur!"
```

#### Модели базы данных (`models.py`)
Определены модели с учётом связей (приведён фрагмент для `Users`):

```python
from typing import Optional, List  
from sqlmodel import SQLModel, Field, Relationship  

class Users(SQLModel, table=True):  
    user_id: Optional[int] = Field(default=None, primary_key=True)  
    username: str = Field(index=True, unique=True)  
    password: str  
    first_name: str  
    last_name: str  
    email: str = Field(unique=True, index=True)  

    transactions: List["Transactions"] = Relationship(back_populates="user")  
    budgets: List["Budgets"] = Relationship(back_populates="user")  
    goals: List["Goals"] = Relationship(back_populates="goals")  
    notifications: List["Notifications"] = Relationship(back_populates="user")
```

#### Схемы Pydantic (`schemas.py`)
Определены модели для валидации данных:

```python
from pydantic import BaseModel, EmailStr  
from typing import Optional  

class UserBase(BaseModel):  
    username: str  
    first_name: str  
    last_name: str  
    email: EmailStr  

class UserCreate(UserBase):  
    password: str  

class UserRead(UserBase):  
    user_id: int  
    class Config:  
        from_attributes = True  

class UserWithToken(BaseModel):  
    user: UserRead  
    access_token: str  
    token_type: str = "bearer"  

class UserLogin(BaseModel):  
    username: str  
    password: str  

class UserPassword(BaseModel):  
    old_password: str  
    new_password: str
```

#### Маршруты авторизации (`routers/auth.py`)
Реализованы функции регистрации, логина, проверки токенов и управления паролем:

```python
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

router = APIRouter(prefix="/auth", tags=["Authentication"])  

SECRET_KEY = os.getenv("SECRET_KEY")  
ALGORITHM = os.getenv("ALGORITHM")  
ACCESS_TOKEN_EXPIRE_MINUTES = 30  

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")  
auth_scheme = HTTPBearer()  

def create_access_token(data: dict, expires_delta: datetime.timedelta = None) -> str:  
    payload = data.copy()  
    if expires_delta:  
        expire = datetime.datetime.now(datetime.timezone.utc) + expires_delta  
    else:  
        expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(  
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES  
        )  
    payload.update({"exp": expire})  
    encoded_jwt = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)  
    return encoded_jwt  

def verify_token(token: str) -> str:  
    try:  
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])  
        return payload.get("sub")  
    except jwt.ExpiredSignatureError:  
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")  
    except jwt.InvalidTokenError:  
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")  

def create_user_with_hash(user_create: UserCreate, session: Session) -> Users:  
    username_statement = select(Users).where(Users.username == user_create.username)  
    existing_user = session.exec(username_statement).first()  
    if existing_user:  
        raise HTTPException(status_code=400, detail="Username already registered")  
    email_statement = select(Users).where(Users.email == user_create.email)  
    existing_email = session.exec(email_statement).first()  
    if existing_email:  
        raise HTTPException(status_code=400, detail="Email already registered")  
    hashed_password = pwd_context.hash(user_create.password)  
    new_user = Users(  
        username=user_create.username,  
        password=hashed_password,  
        first_name=user_create.first_name,  
        last_name=user_create.last_name,  
        email=user_create.email  
    )  
    session.add(new_user)  
    session.commit()  
    session.refresh(new_user)  
    return new_user  

def create_user_and_token(user_create: UserCreate, session: Session) -> dict:  
    user = create_user_with_hash(user_create, session)  
    token = create_access_token(data={"sub": user.username})  
    return {  
        "user": UserRead.model_validate(user),  
        "access_token": token,  
        "token_type": "bearer"  
    }  

@router.post("/register", response_model=UserWithToken)  
def register(user_create: UserCreate, session: Session = Depends(get_session)):  
    return create_user_and_token(user_create, session)  

@router.post("/login", response_model=UserWithToken)  
def login(user_login: UserLogin, session: Session = Depends(get_session)):  
    statement = select(Users).where(Users.username == user_login.username)  
    user = session.exec(statement).first()  
    if not user or not pwd_context.verify(user_login.password, user.password):  
        raise HTTPException(status_code=401, detail="Invalid credentials")  
    token = create_access_token(data={"sub": user.username})  
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
    if not user: raise HTTPException(status_code=404, detail="User not found")  
    return user  

@router.get("/me", response_model=UserRead)  
def read_current_user(current_user: Users = Depends(get_current_user)):  
    return current_user  

@router.patch("/change-password")  
def change_password(  
    pwd_data: UserPassword,  
    current_user: Users = Depends(get_current_user),  
    session: Session = Depends(get_session)  
):  
    if not pwd_context.verify(pwd_data.old_password, current_user.password):  
        raise HTTPException(status_code=400, detail="Incorrect current password")  
    current_user.password = pwd_context.hash(pwd_data.new_password)  
    session.add(current_user)  
    session.commit()  
    return {"message": "Password updated successfully"}
```

#### Маршруты пользователей (`routers/users.py`)
Реализованы CRUD-операции для пользователей:

```python
from fastapi import APIRouter, Depends, HTTPException  
from sqlmodel import Session, select  
from connection import get_session  
from models import Users  
from routers.auth import create_user_and_token  
from schemas import UserCreate, UserRead, UserUpdate, UserWithToken  

router = APIRouter(prefix="/users", tags=["Users"])  

@router.post("/", response_model=UserWithToken)  
def create_user(user_create: UserCreate, session: Session = Depends(get_session)):  
    return create_user_and_token(user_create, session)  

@router.get("/", response_model=list[UserRead])  
def read_users(session: Session = Depends(get_session)):  
    users = session.exec(select(Users)).all()  
    return users  

@router.get("/{user_id}", response_model=UserRead)  
def read_user(user_id: int, session: Session = Depends(get_session)):  
    user = session.get(Users, user_id)  
    if not user:  
        raise HTTPException(status_code=404, detail="User not found")  
    return user  

@router.patch("/{user_id}", response_model=UserRead)  
def update_user(user_id: int, user_update: UserUpdate, session: Session = Depends(get_session)):  
    user = session.get(Users, user_id)  
    if not user:  
        raise HTTPException(status_code=404, detail="User not found")  
    user_data = user_update.dict(exclude_unset=True)  
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
        raise HTTPException(status_code=404, detail="User not found")  
    session.delete(user)  
    session.commit()  
    return {"message": "User deleted successfully"}
```

### Выполнение требований задания

1. Авторизация и регистрация:
	- Реализованы через `POST /auth/register` и `POST /auth/login`. После регистрации пользователь сразу получает JWT-токен.
2. Генерация JWT-токенов:
	- Функция `create_access_token` создаёт токены с использованием библиотеки `jwt`.
3. Аутентификация по JWT-токену:
	- Реализована вручную через `verify_token`, без сторонних библиотек для проверки токена.
4. Хэширование паролей:
	- Используется `passlib` с алгоритмом `bcrypt` для безопасного хранения паролей.
5. Дополнительные API-методы:
	- `GET /auth/me` - получение данных текущего пользователя.
	- `GET /users/` - список всех пользователей.
	- `PATCH /auth/change-password` - смена пароля.

## Результат

Приложение успешно реализует базовый функционал управления пользователями для сервиса личных финансов. Все требования задания выполнены:
- Создана модель данных с более чем 5 таблицами, включая связи one-to-many и many-to-many.
- Реализована авторизация с JWT-токенами вручную.
- Эндпоинты протестированы и доступны через документацию FastAPI.