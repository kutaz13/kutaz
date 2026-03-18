from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy  # pyright: ignore[reportMissingImports] # تم الإضافة للتعامل مع الداتابيز الجديدة
from datetime import datetime             # تم الإضافة لتسجيل وقت الإنتاج
import sqlite3
import nmap
from waitress import serve

app = Flask(__name__)
app.secret_key = 'super_secret_key'

# إعداد قاعدة البيانات الجديدة للإنتاج
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# تعريف جدول الإنتاج (الموديل)
class ProductionLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lot_no = db.Column(db.String(50))
    roll_type = db.Column(db.String(50))
    weight = db.Column(db.Float)
    scrap = db.Column(db.Float)
    joints = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# إنشاء الجداول تلقائياً
with app.app_context():
    db.create_all()

# إعداد قاعدة البيانات للمستخدمين
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)''')
    conn.commit()
    conn.close()

init_db()

# دالة مسح محسنة لتجنب الخطأ 500
def scan_network():
    try:
        nm = nmap.PortScanner()
        nm.scan('127.0.0.1', arguments='-F') 
        devices = []
        for host in nm.all_hosts():
            devices.append({'ip': host, 'status': nm[host].state()})
        return devices if devices else [{'ip': '127.0.0.1', 'status': 'Up'}]
    except:
        return [{'ip': '127.0.0.1', 'status': 'Error: Nmap Failed'}]

@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('index.html', devices=scan_network())

@app.route('/deep-scan')
def deep_scan():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('deep-scan.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute("INSERT INTO users VALUES (?, ?)", (username, password))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return "هذا الاسم مستخدم بالفعل، <a href='/login'>اضغط هنا لتسجيل الدخول</a>"
    return render_template('register.html')   

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()
        if user:
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            return "بيانات الدخول خاطئة!"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/news')
def news():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('news.html')

@app.route('/locations')
def locations():
    return render_template('locations.html')

@app.route('/production_system')
def production_system():
    # جلب آخر 10 تشغيلات لعرضها في الجدول
    logs = ProductionLog.query.order_by(ProductionLog.timestamp.desc()).limit(10).all()
    return render_template('production.html', production_logs=logs)

@app.route('/add_production', methods=['POST'])
def add_production():
    lot_no = request.form.get('lot_no')
    roll_type = request.form.get('roll_type')
    weight = float(request.form.get('weight') or 0)
    scrap = float(request.form.get('scrap') or 0)
    joints = int(request.form.get('joints') or 0)

    new_entry = ProductionLog(
        lot_no=lot_no,
        roll_type=roll_type,
        weight=weight,
        scrap=scrap,
        joints=joints
    )

    db.session.add(new_entry)
    db.session.commit()
    return redirect(url_for('production_system'))

# كود الحذف
@app.route('/delete/<int:id>')
def delete_log(id):
    log = ProductionLog.query.get(id)
    db.session.delete(log)
    db.session.commit()
    return redirect(url_for('production_system'))

# كود التعديل (يفتح صفحة بها البيانات القديمة لتغييرها)
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_log(id):
    log = ProductionLog.query.get(id)
    if request.method == 'POST':
        log.lot_no = request.form['lot_no']
        log.roll_type = request.form['roll_type']
        # ... باقي الحقول ...
        db.session.commit()
        return redirect(url_for('production_system'))
    return render_template('edit.html', log=log)
   
@app.route('/edit_production/<int:id>', methods=['GET', 'POST'])
def edit_production(id):
    log = ProductionLog.query.get_or_404(id)
    
    if request.method == 'POST':
        # سحب البيانات الجديدة من الفورم
        log.order_no = request.form.get('order_no')
        log.lot_no = request.form.get('lot_no')
        log.roll_type = request.form.get('roll_type')
        log.joints = int(request.form.get('joints', 0))
        log.weight = float(request.form.get('weight', 0))
        
        db.session.commit()
        return redirect(url_for('production_system'))
    
    return render_template('edit_production.html', log=log)

@app.route('/delete_production/<int:id>')
def delete_production(id):
    log = ProductionLog.query.get_or_404(id)
    db.session.delete(log)
    db.session.commit() # تأكيد الحذف من قاعدة البيانات
    return redirect(url_for('production_system'))

if __name__ == '__main__':
    print("start server behire")
    serve(app, host='0.0.0.0', port=5000)