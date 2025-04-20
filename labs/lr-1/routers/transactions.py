from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete
from sqlmodel import Session, select
from connection import get_session
from models import Categories, Tags, TransactionTags, TransactionTypeEnums, TransactionTypes, Transactions, Users
from routers.budgets import update_total_spent
from schemas import TransactionCreate, TransactionRead, TransactionTagRead, TransactionUpdate
from routers.auth import get_current_user
from typing import List

router = APIRouter(prefix = "/transactions", tags = ["Transactions"])


@router.post("/", response_model = TransactionRead)
def create_transaction(
    transaction: TransactionCreate,
    current_user: Users = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    transaction_type = session.get(TransactionTypes, transaction.transaction_type_id)
    category = session.get(Categories, transaction.category_id)
    if not transaction_type:
        raise HTTPException(status_code = 404, detail = "Transaction type not found")
    if not category:
        raise HTTPException(status_code = 404, detail = "Category not found")
    if category.transaction_type_id != transaction.transaction_type_id:
        raise HTTPException(status_code = 400, detail = "Category does not match transaction type")

    db_transaction = Transactions(
        user_id = current_user.user_id,
        transaction_type_id = transaction.transaction_type_id,
        category_id = transaction.category_id,
        amount = transaction.amount,
        date = transaction.date,
        description = transaction.description
    )
    session.add(db_transaction)
    session.commit()
    session.refresh(db_transaction)

    for tag_id in transaction.tag_ids or []:
        tag = session.get(Tags, tag_id)
        if not tag:
            raise HTTPException(status_code = 404, detail = f"Tag {tag_id} not found")
        session.add(TransactionTags(tag_id = tag_id, transaction_id = db_transaction.transaction_id))
    session.commit()

    if transaction_type.name == TransactionTypeEnums.expense:
        update_total_spent(
            category_id = transaction.category_id,
            user_id = current_user.user_id,
            session = session
        )

    return db_transaction


@router.get("/tags", response_model = List[TransactionTagRead])
def read_transaction_tags(
    current_user: Users = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    statement = select(TransactionTags).join(Transactions).where(Transactions.user_id == current_user.user_id)
    tags_relations = session.exec(statement).all()
    return tags_relations


@router.get("/", response_model = List[TransactionRead])
def read_transactions(current_user: Users = Depends(get_current_user), session: Session = Depends(get_session)):
    statement = select(Transactions).where(Transactions.user_id == current_user.user_id)
    transactions = session.exec(statement).all()
    return transactions


@router.get("/{transaction_id}", response_model = TransactionRead)
def read_transaction(
    transaction_id: int,
    session: Session = Depends(get_session),
    current_user: Users = Depends(get_current_user)
):
    transaction = session.get(Transactions, transaction_id)
    if not transaction:
        raise HTTPException(status_code = 404, detail = "Transaction not found")
    if transaction.user_id != current_user.user_id:
        raise HTTPException(status_code = 403, detail = "Not authorized to view this transaction")
    return transaction


@router.patch("/{transaction_id}", response_model = TransactionRead)
def update_transaction(
    transaction_id: int,
    upd: TransactionUpdate,
    current_user: Users = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    transactions = session.get(Transactions, transaction_id)
    if not transactions:
        raise HTTPException(status_code = 404, detail = "Transaction not found")
    if transactions.user_id != current_user.user_id:
        raise HTTPException(status_code = 403, detail = "Not authorized")

    old_category = transactions.category_id
    data = upd.dict(exclude_unset = True, exclude_none = True)

    if 'transaction_type_id' in data:
        tt = session.get(TransactionTypes, data['transaction_type_id'])
        if not tt:
            raise HTTPException(status_code = 404, detail = "Type not found")
    if 'category_id' in data:
        cat = session.get(Categories, data['category_id'])
        if not cat or (data.get('transaction_type_id') and cat.transaction_type_id != data['transaction_type_id']):
            raise HTTPException(status_code = 400, detail = "Category/type mismatch")

    for k, v in data.items():
        if k != 'tag_ids':
            setattr(transactions, k, v)

    if upd.tag_ids is not None:
        session.exec(
            delete(TransactionTags).where(TransactionTags.transaction_id == transaction_id)
        )
        for tag_id in upd.tag_ids:
            tag = session.get(Tags, tag_id)
            if not tag:
                raise HTTPException(status_code = 404, detail = f"Tag {tag_id} not found")
            session.add(TransactionTags(tag_id = tag_id, transaction_id = transaction_id))

    session.add(transactions)
    session.commit()
    session.refresh(transactions)

    if transactions.transaction_type.name == TransactionTypeEnums.expense:
        update_total_spent(
            category_id = transactions.category_id,
            user_id = current_user.user_id,
            session = session
        )
        if old_category != transactions.category_id:
            update_total_spent(
                category_id = old_category,
                user_id = current_user.user_id,
                session = session
            )

    return transactions


@router.delete("/{transaction_id}")
def delete_transaction(
    transaction_id: int,
    current_user: Users = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    transaction = session.get(Transactions, transaction_id)
    if not transaction:
        raise HTTPException(status_code = 404, detail = "Transaction not found")
    if transaction.user_id != current_user.user_id:
        raise HTTPException(status_code = 403, detail = "Not authorized to delete this transaction")

    category_id = transaction.category_id
    transaction_type = session.get(TransactionTypes, transaction.transaction_type_id)

    session.delete(transaction)
    session.commit()

    if transaction_type.name == TransactionTypeEnums.expense:
        update_total_spent(
            category_id = category_id,
            user_id = current_user.user_id,
            session = session
        )

    return {"message": "Transaction deleted successfully"}
