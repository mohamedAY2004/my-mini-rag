from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings (BaseSettings):
    APP_NAME: str
    APP_VERSION: str
    APP_DESCRIPTION: str
    APP_AUTHOR: str
    class Config:
        env_file = ".env"
def get_settings():
    return Settings()