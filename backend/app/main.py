import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.routes import (
    audit_logs,
    auth,
    branches,
    cars,
    customers,
    dashboard,
    maintenance,
    payments,
    rentals,
    reservations,
    users,
)
from app.core.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("fleetrent")

app = FastAPI(
    title="FleetRent API",
    version="1.0.0",
    # Interactive docs are only exposed in development
    docs_url="/api/docs" if settings.is_development else None,
    redoc_url=None,
    openapi_url="/api/openapi.json" if settings.is_development else None,
)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts_list)
if settings.cors_origins_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    )


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"  # API responses contain personal data
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    return response


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError):
    # Do not echo submitted values (could contain passwords) back to the client
    errors = [
        {"loc": [str(p) for p in e.get("loc", ())], "msg": e.get("msg", "Invalid value")} for e in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": errors})


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    # Log the full error server-side, never leak stack traces to clients
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


for module in (auth, users, branches, cars, customers, reservations, rentals, payments, maintenance, dashboard, audit_logs):
    app.include_router(module.router, prefix="/api")


@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok"}
