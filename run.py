import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # threaded=True — нужен для SSE: один поток держит длинное соединение,
    # другие потоки обрабатывают POST-запросы, которые публикуют события.
    app.run(debug=True, port=port, threaded=True)
    app.run(debug=True, host='0.0.0.0', port=port)
