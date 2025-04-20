from fastapi import FastAPI

from connection import init_db
from routers import auth, budgets, categories, notifications, tags, transactions, users

app = FastAPI()


@app.on_event("startup")
def on_startup():
    init_db()


app.include_router(auth.router)
app.include_router(budgets.router)
app.include_router(categories.router)
app.include_router(notifications.router)
app.include_router(tags.router)
app.include_router(transactions.router)
app.include_router(users.router)


@app.get("/")
def hello():
    return "Hello, Artur!"
