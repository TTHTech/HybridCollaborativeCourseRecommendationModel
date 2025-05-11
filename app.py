from app import create_app

app = create_app()

if __name__ == "__main__":
    # Khởi chạy Flask app
    port = int(app.config.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=app.config.get("DEBUG", False))