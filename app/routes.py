import time
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, g

from app import recommender

logger = logging.getLogger("recommendation-api")

# Cache đơn giản
recommendation_cache = {}
cache_stats = {"hits": 0, "misses": 0, "last_cleanup": time.time()}


def register_routes(app):
    """Đăng ký các routes cho app Flask"""

    @app.before_request
    def before_request():
        """Lưu thời gian bắt đầu request"""
        g.start_time = time.time()

    @app.after_request
    def after_request(response):
        """Thêm thời gian xử lý vào response"""
        if hasattr(g, 'start_time'):
            response_time = time.time() - g.start_time

            try:
                if response.is_json:
                    data = response.get_json()
                    if isinstance(data, dict):
                        data["response_time_s"] = round(response_time, 3)
                        response.data = jsonify(data).data
            except:
                pass

        return response

    @app.route("/")
    def root():
        """Endpoint root"""
        return jsonify({
            "name": "MultiSkill Academy Recommendation API",
            "version": "1.0.0",
            "status": "running",
            "startup_time": recommender.startup_time.isoformat() if recommender else None
        })

    @app.route("/api/status")
    def api_status():
        """Endpoint trạng thái"""
        model_info = recommender.get_info() if recommender else {}

        return jsonify({
            "status": "running",
            "api_version": "1.0.0",
            "model_loaded": recommender is not None and recommender.is_loaded(),
            "users_count": model_info.get("user_count", 0),
            "courses_count": model_info.get("item_count", 0),
            "mine_courses_count": model_info.get("mine_count", 0),
            "cache": {
                "size": len(recommendation_cache),
                "hits": cache_stats["hits"],
                "misses": cache_stats["misses"]
            },
            "model_info": model_info.get("metadata", {})
        })

    @app.route("/api/recommendations")
    def api_recommendations():
        """Endpoint đề xuất khóa học"""
        # Kiểm tra model đã được tải chưa
        if not recommender or not recommender.is_loaded():
            return jsonify({
                "error": "Model chưa được tải, không thể đưa ra đề xuất"
            }), 503

        # Lấy và validate user_id
        user_id = request.args.get("user_id")
        if not user_id:
            return jsonify({"error": "Thiếu tham số user_id"}), 400

        # Tham số khác
        count = min(int(request.args.get("count", app.config["DEFAULT_REC_COUNT"])),
                    app.config["MAX_REC_COUNT"])
        mine_only = request.args.get("mine_only", "true").lower() in ["true", "1", "yes"]

        # Tạo cache key
        cache_key = f"{user_id}_{count}_{mine_only}"

        # Kiểm tra cache
        now = time.time()
        if cache_key in recommendation_cache and now - recommendation_cache[cache_key]["time"] < app.config[
            "CACHE_TTL"]:
            cache_stats["hits"] += 1
            return jsonify(recommendation_cache[cache_key]["data"])

        cache_stats["misses"] += 1

        # Gọi model để lấy đề xuất
        try:
            recommendations = recommender.recommend(user_id, count, mine_only)

            # Lưu cache
            recommendation_cache[cache_key] = {
                "data": recommendations,
                "time": now
            }

            # Dọn cache nếu quá lớn
            if len(recommendation_cache) > app.config["MAX_CACHE_SIZE"]:
                oldest = sorted(recommendation_cache.items(), key=lambda x: x[1]["time"])
                recommendation_cache.clear()
                recommendation_cache.update(dict(oldest[:app.config["MAX_CACHE_SIZE"] // 2]))

            return jsonify(recommendations)
        except Exception as e:
            logger.error(f"Lỗi khi đề xuất cho user {user_id}: {str(e)}")
            return jsonify({
                "error": f"Không thể đưa ra đề xuất: {str(e)}"
            }), 500

    @app.route("/api/users")
    def api_users():
        """Endpoint lấy danh sách user IDs"""
        if not recommender or not recommender.is_loaded():
            return jsonify({"error": "Model chưa được tải"}), 503

        limit = int(request.args.get("limit", 100))
        offset = int(request.args.get("offset", 0))

        users = recommender.get_users()
        total = len(users)

        return jsonify({
            "total": total,
            "offset": offset,
            "limit": limit,
            "users": users[offset:offset + limit]
        })

    @app.route("/api/courses")
    def api_courses():
        """Endpoint lấy danh sách khóa học"""
        if not recommender or not recommender.is_loaded():
            return jsonify({"error": "Model chưa được tải"}), 503

        source = request.args.get("source")  # "mine" hoặc "udemy"
        limit = int(request.args.get("limit", 100))

        courses = recommender.get_courses(source)

        return jsonify({
            "total": len(courses),
            "source": source,
            "limit": limit,
            "courses": courses[:limit]
        })

    logger.info("✓ Đã đăng ký tất cả routes")