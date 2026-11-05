from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./work/echoloom.db"
    image_directory: Path = Path("work/portraits")
    llm_provider: str = "openai"
    llm_model: str = ""
    llm_api_key: SecretStr = SecretStr("")
    image_provider: str = "openai"
    image_model: str = ""
    image_api_key: SecretStr = SecretStr("")
    max_profile_input_chars: int = Field(5000, ge=100, le=20000)
    max_chat_context_tokens: int = Field(12000, ge=2000, le=64000)
    max_output_tokens: int = Field(1500, ge=128, le=8000)
    max_image_bytes: int = Field(10 * 1024 * 1024, ge=1024, le=25 * 1024 * 1024)
    image_requests_per_hour: int = Field(6, ge=1, le=100)
    api_timeout_seconds: float = Field(90, ge=1, le=300)
    story_max_output_tokens: int = Field(3500, ge=1000, le=8000)
    story_max_context_tokens: int = Field(24000, ge=6000, le=64000)
