from fastapi import APIRouter
from starlette.responses import RedirectResponse
from app.esi import esi_manager
router = APIRouter(prefix="/auth")

@router.get("/login")
def login():
    auth_url = esi_manager.get_auth_url()
    return RedirectResponse(url=auth_url)

@router.get("/callback")
def callback(code: str):
    esi_manager.authenticate(code)
    return {"message": "Authenticated successfully"}

