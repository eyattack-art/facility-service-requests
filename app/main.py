import uvicorn

from app.core.config import settings
from app.core.factory import create_app

app = create_app(settings=settings)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host=settings.app.host, port=settings.app.port, reload=True)
