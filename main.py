from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from database import create_tables
from router import router as router

app = FastAPI(
    title="Payment Methods API",
    description="Card, UPI, and Bank account management",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    create_tables()


app.include_router(router)


@app.get("/")
def root():
    return RedirectResponse(url="/docs")
