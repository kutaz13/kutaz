from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    # هنا تضع كل بيانات الفروع التي أرسلتها
    branches = [
        {"name": "Cogebi Belgium", "contact": "+32 2 334 91 11"},
        {"name": "Cogebi Egypt", "contact": "+202 21810320"}
    ]
    return render_template('index.html', branches=branches)
from waitress import serve
if __name__ == '__main__':
   serve (app, host='0.0.0.0', port=5000)