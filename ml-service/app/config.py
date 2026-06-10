from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://discordia:discordia@postgres:5432/discordia"
    backend_url: str = "http://backend:8000"

    class Config:
        env_file = ".env"


settings = Settings()
