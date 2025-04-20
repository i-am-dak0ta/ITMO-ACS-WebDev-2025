from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func
from sqlmodel import Session, select
from connection import get_session
from models import Budgets, Categories, Notifications, TransactionTypeEnums, TransactionTypes, Transactions, Users
from schemas import BudgetCreate, BudgetRead, BudgetUpdate
from routers.auth import get_current_user
from typing import List

router = APIRouter(prefix = "/budgets", tags = ["Budgets"])


@router.post("/", response_model = BudgetRead)
def create_budget(
    budget: BudgetCreate,
    current_user: Users = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    category = session.get(Categories, budget.category_id)
    if not category:
        raise HTTPException(status_code = 404, detail = "Category not found")
    if category.transaction_type.name != TransactionTypeEnums.expense:
        raise HTTPException(status_code = 400, detail = "Budget can only be set for expense categories")

    db_budget = Budgets(
        user_id = current_user.user_id,
        category_id = budget.category_id,
        limit_amount = budget.limit_amount,
        start_date = budget.start_date,
        end_date = budget.end_date,
        description = budget.description
    )
    session.add(db_budget)
    session.commit()
    session.refresh(db_budget)

    update_total_spent(
        category_id = budget.category_id,
        user_id = current_user.user_id,
        session = session
    )

    return db_budget


@router.get("/", response_model = List[BudgetRead])
def read_budgets(
    current_user: Users = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    statement = select(Budgets).where(Budgets.user_id == current_user.user_id)
    budgets = session.exec(statement).all()
    return budgets


@router.get("/{budget_id}", response_model = BudgetRead)
def read_budget(
    budget_id: int,
    current_user: Users = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    budget = session.get(Budgets, budget_id)
    if not budget:
        raise HTTPException(status_code = 404, detail = "Budget not found")
    if budget.user_id != current_user.user_id:
        raise HTTPException(status_code = 403, detail = "Not authorized to view this budget")
    return budget


def update_total_spent(category_id: int, user_id: int, session: Session):
    expense_type = session.exec(
        select(TransactionTypes).where(TransactionTypes.name == TransactionTypeEnums.expense)
    ).first()

    budgets = session.exec(
        select(Budgets).where(
            Budgets.category_id == category_id,
            Budgets.user_id == user_id
        )
    ).all()

    for budget in budgets:
        total = session.exec(
            select(func.sum(Transactions.amount)).where(
                Transactions.user_id == budget.user_id,
                Transactions.category_id == budget.category_id,
                Transactions.transaction_type_id == expense_type.transaction_type_id,
                Transactions.date.between(budget.start_date, budget.end_date)
            )
        ).first()

        total = total if total is not None else 0.0

        budget.total_spent = total
        session.add(budget)

        if total <= budget.limit_amount:
            session.exec(
                delete(Notifications).where(
                    Notifications.user_id == budget.user_id,
                    Notifications.budget_id == budget.budget_id
                )
            )
        else:
            exists = session.exec(
                select(Notifications).where(
                    Notifications.user_id == budget.user_id,
                    Notifications.budget_id == budget.budget_id
                )
            ).first()
            if not exists:
                session.add(
                    Notifications(
                        user_id = budget.user_id,
                        budget_id = budget.budget_id,
                        message = (
                            f"Бюджет по категории «{budget.category.name}» превышен: "
                            f"потрачено {total}, лимит {budget.limit_amount}"
                        )
                    )
                )
    session.commit()


@router.patch("/{budget_id}", response_model = BudgetRead)
def update_budget(
    budget_id: int,
    budget_update: BudgetUpdate,
    current_user: Users = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    budget = session.get(Budgets, budget_id)
    if not budget:
        raise HTTPException(status_code = 404, detail = "Budget not found")
    if budget.user_id != current_user.user_id:
        raise HTTPException(status_code = 403, detail = "Not authorized to update this budget")

    data = budget_update.dict(exclude_unset = True)
    if 'category_id' in data:
        category = session.get(Categories, data['category_id'])
        if not category or category.transaction_type.name != TransactionTypeEnums.expense:
            raise HTTPException(status_code = 400, detail = "Invalid expense category")
    for k, v in data.items():
        setattr(budget, k, v)
    session.add(budget)
    session.commit()
    session.refresh(budget)

    update_total_spent(
        category_id = budget.category_id,
        user_id = current_user.user_id,
        session = session
    )
    return budget


@router.delete("/{budget_id}")
def delete_budget(
    budget_id: int,
    current_user: Users = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    budget = session.get(Budgets, budget_id)
    if not budget:
        raise HTTPException(status_code = 404, detail = "Budget not found")
    if budget.user_id != current_user.user_id:
        raise HTTPException(status_code = 403, detail = "Not authorized to delete this budget")
    session.delete(budget)
    session.commit()
    return {"message": "Budget deleted successfully"}
