from fastapi import APIRouter
from app.api.routes import google_auth, auth, user_router,exam_router, report_router

router = APIRouter()

router.include_router(auth.router)
router.include_router(google_auth.router)
router.include_router(user_router.router)
router.include_router(exam_router.router)
router.include_router(report_router.router)