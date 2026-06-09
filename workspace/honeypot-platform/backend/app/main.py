from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


from app.api.auth import router as auth_router
from app.api.dashboard import router as dashboard_router
from app.api.sessions import router as session_router
from app.api.honeypots import router as honeypot_router
from app.api.security import ensure_security_schema


app = FastAPI(title="Honeypot Platform API")

ensure_security_schema()

app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(session_router)
app.include_router(honeypot_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "honeypot-platform-backend",
    }
