import time
import threading
import webbrowser
from app import app

URL = "http://127.0.0.1:5000"

def open_browser():
    time.sleep(1.2)
    webbrowser.open(URL)

if __name__ == "__main__":
    threading.Thread(target=open_browser, daemon=True).start()
    print("Тверь.Гид запущен.")
    print("Адрес сайта: " + URL)
    print("Не закрывайте это окно, пока пользуетесь сайтом.")
    print("Чтобы остановить сайт, нажмите Ctrl+C или закройте это окно.")
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
