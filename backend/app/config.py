from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://discordia:discordia@localhost:5432/discordia"
    redis_url: str = "redis://localhost:6379"
    kafka_bootstrap_servers: str = "localhost:9092"
    anthropic_api_key: str = ""
    ml_service_url: str = "http://localhost:8001"

    class Config:
        env_file = ".env"


settings = Settings()
