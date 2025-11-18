from fastapi import APIRouter
from starlette.responses import RedirectResponse
from app.esi import authenticate, get_auth_url
router = APIRouter(prefix="/auth")

@router.get("/login")
def login():
    auth_url = get_auth_url()
    return RedirectResponse(url=auth_url)

@router.get("/callback")
def callback(code: str):
    authenticate(code)
    return {"message": "Authenticated successfully"}

