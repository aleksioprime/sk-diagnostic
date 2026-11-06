from fastapi import APIRouter
from sk_common.people.router import router as people_router

from app.modules.assignments.router import router as psychologists_router
from app.modules.attempts.router import router as my_router
from app.modules.auth import router as auth_router
from app.modules.directory.router import router as directory_router
from app.modules.system.router import router as system_router
from app.modules.tests.router import router as tests_router

api_router = APIRouter(prefix='/api')
api_router.include_router(system_router)
api_router.include_router(auth_router)
api_router.include_router(people_router)
api_router.include_router(directory_router)
api_router.include_router(my_router)
api_router.include_router(psychologists_router)
api_router.include_router(tests_router)
