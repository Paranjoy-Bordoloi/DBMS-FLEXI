from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


BACKEND_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(BACKEND_ROOT / '.env'), '.env'),
        env_file_encoding='utf-8',
        extra='ignore',
    )

    db_user: str = Field(default='root', alias='DB_USER')
    db_password: str = Field(default='', alias='DB_PASSWORD')
    db_host: str = Field(default='localhost', alias='DB_HOST')
    db_port: int = Field(default=3306, alias='DB_PORT')
    db_name: str = Field(default='airline_reservation', alias='DB_NAME')

    jwt_secret: str = Field(default='change-me-in-env', alias='JWT_SECRET')
    jwt_algorithm: str = Field(default='HS256', alias='JWT_ALGORITHM')
    access_token_expire_minutes: int = Field(default=60, alias='ACCESS_TOKEN_EXPIRE_MINUTES')

    @property
    def database_url(self) -> str:
        return URL.create(
            drivername='mysql+pymysql',
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        ).render_as_string(hide_password=False)


settings = Settings()
