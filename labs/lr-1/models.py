from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from enum import Enum


class Users(SQLModel, table = True):
    user_id: Optional[int] = Field(default = None, primary_key = True)
    username: str = Field(index = True, unique = True)
    password: str
    first_name: str
    last_name: str
    email: str = Field(unique = True, index = True)

    transactions: List["Transactions"] = Relationship(back_populates = "user")
    budgets: List["Budgets"] = Relationship(back_populates = "user")
    notifications: List["Notifications"] = Relationship(back_populates = "user")


class TransactionTypeEnums(str, Enum):
    income = "income"
    expense = "expense"


class TransactionTypes(SQLModel, table = True):
    transaction_type_id: Optional[int] = Field(default = None, primary_key = True)
    name: TransactionTypeEnums

    transactions: List["Transactions"] = Relationship(back_populates = "transaction_type")
    categories: List["Categories"] = Relationship(back_populates = "transaction_type")


class Categories(SQLModel, table = True):
    category_id: Optional[int] = Field(default = None, primary_key = True)
    transaction_type_id: Optional[int] = Field(default = None, foreign_key = "transactiontypes.transaction_type_id")
    name: str

    transactions: List["Transactions"] = Relationship(back_populates = "category")
    budgets: List["Budgets"] = Relationship(back_populates = "category")
    transaction_type: Optional["TransactionTypes"] = Relationship(back_populates = "categories")


class Budgets(SQLModel, table = True):
    budget_id: Optional[int] = Field(default = None, primary_key = True)
    user_id: Optional[int] = Field(foreign_key = "users.user_id")
    category_id: Optional[int] = Field(foreign_key = "categories.category_id")
    limit_amount: float
    start_date: datetime
    end_date: datetime
    description: Optional[str] = None
    total_spent: float = Field(default = 0.0)

    user: Optional["Users"] = Relationship(back_populates = "budgets")
    category: Optional["Categories"] = Relationship(back_populates = "budgets")
    notifications: List["Notifications"] = Relationship(back_populates = "budget")


class Notifications(SQLModel, table = True):
    notification_id: Optional[int] = Field(default = None, primary_key = True)
    user_id: Optional[int] = Field(foreign_key = "users.user_id")
    budget_id: Optional[int] = Field(foreign_key = "budgets.budget_id")
    message: str
    created_at: datetime = Field(default_factory = datetime.utcnow)
    is_read: bool = Field(default = False)

    user: Optional["Users"] = Relationship(back_populates = "notifications")
    budget: Optional["Budgets"] = Relationship(back_populates = "notifications")


class TransactionTags(SQLModel, table = True):
    transaction_tag_id: Optional[int] = Field(default = None, primary_key = True)
    tag_id: Optional[int] = Field(foreign_key = "tags.tag_id")
    transaction_id: Optional[int] = Field(foreign_key = "transactions.transaction_id")
    created_at: datetime = Field(default_factory = datetime.utcnow)


class Tags(SQLModel, table = True):
    tag_id: Optional[int] = Field(default = None, primary_key = True)
    name: str

    transactions: List["Transactions"] = Relationship(back_populates = "tags", link_model = TransactionTags)


class Transactions(SQLModel, table = True):
    transaction_id: Optional[int] = Field(default = None, primary_key = True)
    user_id: Optional[int] = Field(foreign_key = "users.user_id")
    transaction_type_id: Optional[int] = Field(foreign_key = "transactiontypes.transaction_type_id")
    category_id: Optional[int] = Field(foreign_key = "categories.category_id")
    amount: float
    date: datetime
    description: Optional[str] = None

    user: Optional["Users"] = Relationship(back_populates = "transactions")
    transaction_type: Optional["TransactionTypes"] = Relationship(back_populates = "transactions")
    category: Optional["Categories"] = Relationship(back_populates = "transactions")
    tags: List["Tags"] = Relationship(back_populates = "transactions", link_model = TransactionTags)
