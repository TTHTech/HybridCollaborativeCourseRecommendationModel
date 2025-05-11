import os
import logging
from flask import Flask
from flask_cors import CORS

from models.recommender import RecommenderModel
from config import Config

# Khởi tạo logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("recommendation-api")

# Biến toàn cục cho model
recommender = None


def create_app():
    """Tạo và cấu hình Flask app"""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Cấu hình CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Đảm bảo thư mục models tồn tại
    os.makedirs(os.path.dirname(app.config['MODEL_PATH']), exist_ok=True)

    # Tải model
    global recommender
    recommender = RecommenderModel(app.config['MODEL_PATH'])
    if not recommender.load():
        logger.warning("⚠️ Không thể tải model - API sẽ hoạt động hạn chế")

    # Đăng ký routes
    from app.routes import register_routes
    register_routes(app)

    logger.info("✓ Đã khởi tạo Flask app!")
    return app