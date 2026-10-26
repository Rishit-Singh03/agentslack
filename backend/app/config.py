from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./agentslack.db"
    relay_key: str | None = None
    relay_base_url: str | None = None
    relay_base_url_v1: str | None = None
    relay_reserve_url: str | None = None
    relay_reserve_url_v1: str | None = None
    deepseek_api_key: str | None = None
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    openrouter_api_key: str | None = None
    runtime_data_dir: str = "./data/runtime"
    pi_idle_ttl: float = 300
    pi_queue_size: int = 8
    pi_timeout: float = 180
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    @model_validator(mode="after")
    def relay_aliases(self):
        self.relay_base_url = self.relay_base_url or self.relay_base_url_v1
        self.relay_reserve_url = self.relay_reserve_url or self.relay_reserve_url_v1
        return self


settings = Settings()
