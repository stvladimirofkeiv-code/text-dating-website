import os


class Settings:
    def __init__(self) -> None:
        self.env = os.environ.get("ENV", "development")
        self.database_url = os.environ.get("DATABASE_URL", "sqlite:///./dev.db")
        self.min_messages_each = int(os.environ.get("MIN_MESSAGES_EACH", "5"))
        key = os.environ.get("SECRET_KEY")
        if not key:
            if self.env == "production":
                raise RuntimeError("SECRET_KEY must be set in production")
            key = "dev-only-insecure-key"
        self.secret_key = key

    @property
    def is_prod(self) -> bool:
        return self.env == "production"


settings = Settings()
