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
