import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.requests import Request
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.routers import rooms, bookings

app = FastAPI(title=settings.project_name, version=settings.version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rooms.router)
app.include_router(bookings.router)


@app.get("/")
def root():
    return {"status": "Running"}


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
    if constraint == "no_overlapping_room_bookings":
        return JSONResponse(
            status_code=409, content={"detail": "Time slot was just taken"}
        )
    raise exc


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
