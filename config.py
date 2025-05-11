import os


class Config:
    # API Config
    PORT = int(os.environ.get("PORT", 5000))
    DEBUG = os.environ.get("DEBUG", "False").lower() == "true"

    # Model Config
    MODEL_PATH = os.environ.get("MODEL_PATH", "models/recommendation_model.pkl")

    # Google Drive model file ID (example link:
    # https://drive.google.com/file/d/1ZYD-r8Tock-a4kSL5WDRY4LTJJh4Pdog/view?usp=sharing)
    # → ID là phần "1ZYD-r8Tock-a4kSL5WDRY4LTJJh4Pdog"
    GDRIVE_MODEL_ID = os.environ.get("GDRIVE_MODEL_ID", "1ZYD-r8Tock-a4kSL5WDRY4LTJJh4Pdog")

    # Cache Config
    CACHE_TTL = int(os.environ.get("CACHE_TTL", 3600))  # 1 giờ
    MAX_CACHE_SIZE = int(os.environ.get("MAX_CACHE_SIZE", 1000))

    # Database Config
    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_PORT = int(os.environ.get("DB_PORT", 3306))
    DB_USER = os.environ.get("DB_USER", "root")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "123456")
    DB_NAME = os.environ.get("DB_NAME", "courses_data")

    # API Recommender Config
    DEFAULT_REC_COUNT = 10
    MAX_REC_COUNT = 50
