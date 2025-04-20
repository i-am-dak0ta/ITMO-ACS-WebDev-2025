from pydantic import BaseModel, EmailStr, field_validator, validator
from typing import Optional, List
from datetime import datetime

from pydantic_core.core_schema import ValidationInfo


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


class UserUpdate(BaseModel):
    first_name: Optional[str]
    last_name: Optional[str]
    email: Optional[EmailStr]


class UserLogin(BaseModel):
    username: str
    password: str


class UserPassword(BaseModel):
    old_password: str
    new_password: str


class TransactionBase(BaseModel):
    amount: float
    date: datetime
    description: Optional[str] = None


class TransactionCreate(TransactionBase):
    transaction_type_id: int
    category_id: int
    tag_ids: Optional[List[int]] = []

    @field_validator('amount')
    def amount_must_be_positive(cls, amount: float):
        if amount <= 0:
            raise ValueError('Amount must be positive')
        return amount


class TransactionUpdate(BaseModel):
    transaction_type_id: Optional[int]
    category_id: Optional[int]
    amount: Optional[float]
    date: Optional[datetime]
    description: Optional[str] = None
    tag_ids: Optional[List[int]]

    @field_validator('amount')
    def amount_must_be_positive(cls, amount: Optional[float]):
        if amount is not None and amount <= 0:
            raise ValueError('Amount must be positive')
        return amount


class TransactionRead(TransactionBase):
    transaction_id: int
    user_id: int
    transaction_type_id: int
    category_id: int
    tags: List['TagRead'] = []

    class Config:
        from_attributes = True


class BudgetBase(BaseModel):
    limit_amount: float
    start_date: datetime
    end_date: datetime
    description: Optional[str] = None


class BudgetCreate(BudgetBase):
    category_id: int

    @field_validator('limit_amount')
    def limit_amount_must_be_positive(cls, limit_amount: float):
        if limit_amount <= 0:
            raise ValueError('Limit amount must be positive')
        return limit_amount

    @field_validator('end_date')
    def check_dates(cls, end_date: datetime, info: ValidationInfo):
        start_date = info.data.get('start_date')  # type: ignore
        if start_date and end_date <= start_date:
            raise ValueError('End date must be after start date')
        return end_date


class BudgetUpdate(BaseModel):
    category_id: Optional[int]
    limit_amount: Optional[float]
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    description: Optional[str] = None

    @field_validator('limit_amount')
    def limit_amount_must_be_positive(cls, limit_amount: Optional[float]):
        if limit_amount is not None and limit_amount <= 0:
            raise ValueError('Limit amount must be positive')
        return limit_amount

    @field_validator('end_date')
    def check_dates(cls, end_date: datetime, info: ValidationInfo):
        start_date = info.data.get('start_date')  # type: ignore
        if start_date and end_date <= start_date:
            raise ValueError('End date must be after start date')
        return end_date


class BudgetRead(BudgetBase):
    budget_id: int
    user_id: int
    category_id: int
    total_spent: float

    class Config:
        from_attributes = True


class NotificationRead(BaseModel):
    notification_id: int
    user_id: int
    budget_id: int
    message: str
    created_at: datetime
    is_read: bool

    class Config:
        from_attributes = True


class CategoryBase(BaseModel):
    name: str


class CategoryRead(CategoryBase):
    category_id: int
    transaction_type_id: int

    class Config:
        from_attributes = True


class TagBase(BaseModel):
    name: str


class TagRead(TagBase):
    tag_id: int

    class Config:
        from_attributes = True


class TransactionTagRead(BaseModel):
    transaction_tag_id: int
    tag_id: int
    transaction_id: int
    created_at: datetime

    class Config:
        from_attributes = True
