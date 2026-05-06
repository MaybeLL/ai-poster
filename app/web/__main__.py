from app.web.app import app


if __name__ == "__main__":
    import uvicorn

    settings = app.state.settings
    uvicorn.run(
        "app.web.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
