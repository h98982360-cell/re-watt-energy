from pydantic_settings import BaseSettings, SettingsConfigDict

# The Settings class reads the .env file and makes the values available to the rest of the app.
class Settings(BaseSettings):
    groq_api_key: str
    groq_model: str
    llm_timeout_seconds: float
    ai_service_api_key: str
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
