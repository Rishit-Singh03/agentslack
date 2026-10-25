from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./agentslack.db"
    relay_key: str | None = None
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")


settings = Settings()
