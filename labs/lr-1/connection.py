import os
from dotenv import load_dotenv
from sqlmodel import SQLModel, Session, create_engine, select

from models import Categories, Tags, TransactionTypeEnums, TransactionTypes

load_dotenv()
db_url = os.getenv("DB_ADMIN")
engine = create_engine(db_url, echo = True)
DEFAULT_TAGS = ["impulse_buy", "planned_buy", "cash", "card"]
DEFAULT_TRANSACTION_TYPES = ["income", "expense"]
DEFAULT_CATEGORIES = {
    "expense": [
        {"name": "groceries"},
        {"name": "transport"},
        {"name": "housing"},
        {"name": "health"},
        {"name": "entertainment"},
        {"name": "other_expenses"},
    ],
    "income": [
        {"name": "salary"},
        {"name": "investments"},
    ],
}


def init_db():
    SQLModel.metadata.create_all(engine)
    init_default_tags()
    init_default_transaction_types()
    init_default_categories()


def init_default_tags():
    with Session(engine) as session:
        for tag_name in DEFAULT_TAGS:
            tag_exists = session.exec(select(Tags).where(Tags.name == tag_name)).first()
            if not tag_exists:
                session.add(Tags(name = tag_name))
        session.commit()


def init_default_transaction_types():
    with Session(engine) as session:
        for tt_name in DEFAULT_TRANSACTION_TYPES:
            type_exists = session.exec(
                select(TransactionTypes).where(TransactionTypes.name == tt_name)
            ).first()
            if not type_exists:
                session.add(TransactionTypes(name=tt_name))
        session.commit()


def init_default_categories():
    with Session(engine) as session:
        for tx_type_str, categories in DEFAULT_CATEGORIES.items():
            tx_type = session.exec(
                select(TransactionTypes).where(TransactionTypes.name == TransactionTypeEnums(tx_type_str))
            ).first()

            if not tx_type:
                continue

            for category in categories:
                exists = session.exec(
                    select(Categories).where(
                        Categories.name == category["name"],
                        Categories.transaction_type_id == tx_type.transaction_type_id
                    )
                ).first()

                if not exists:
                    session.add(
                        Categories(
                            name = category["name"],
                            transaction_type_id = tx_type.transaction_type_id
                        )
                    )

        session.commit()


def get_session():
    with Session(engine) as session:
        yield session
