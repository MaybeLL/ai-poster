import uvicorn

from app.web.app import app
from app.web.state import get_settings


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "app.web.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
