from flask import Flask, render_template, redirect, url_for, request, flash, session
import mysql.connector
from mysql.connector import Error
from functools import wraps
from datetime import datetime
from dotenv import load_dotenv
import os
import logging

# Memuat variabel dari file .env
load_dotenv()

# Inisialisasi aplikasi Flask
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "default_secret_key")  # Gunakan default yang aman

# Konfigurasi logging
logging.basicConfig(level=logging.INFO)  # Ganti INFO dengan DEBUG untuk debugging
logger = logging.getLogger(__name__)

# Koneksi ke database MySQL menggunakan konfigurasi dari .env
def get_db_connection():
    try:
        # Ambil konfigurasi dari .env
        db_config = {
            "host": os.getenv("DB_HOST", "localhost"),
            "user": os.getenv("DB_USER", "root"),
            "password": os.getenv("DB_PASSWORD", ""),
            "database": os.getenv("DB_NAME", "test_db"),
            "port": int(os.getenv("DB_PORT", 3306)),  # Konversi ke integer
        }

        # Validasi konfigurasi kritis
        if not db_config["host"] or not db_config["user"] or not db_config["database"]:
            logger.error("Konfigurasi database tidak lengkap. Harap periksa file .env.")
            return None

        # Membuka koneksi
        connection = mysql.connector.connect(**db_config)
        logger.info("Koneksi ke database berhasil.")
        return connection

    except Error as e:
        logger.error(f"Kesalahan saat menghubungkan ke database: {e}")
        return None
    
@app.route('/check_db')
def check_db():
    try:
        connection = get_db_connection()
        connection.close()
        return "Database connection successful!"
    except Exception as e:
        return f"Database connection failed: {e}"

# Decorator untuk mengecek login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Silakan login terlebih dahulu.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Route untuk halaman utama
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('home.html')

# Route untuk login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Mohon isi semua field.', 'danger')
            return render_template('login.html')

        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", 
                             (username, password))
                user = cursor.fetchone()
                
                if user:
                    session['user_id'] = user['id']
                    session['username'] = user['username']
                    flash(f'Selamat datang, {user["username"]}!', 'success')
                    return redirect(url_for('dashboard'))
                else:
                    flash('Username atau password salah.', 'danger')
            except Error as e:
                flash('Terjadi kesalahan database.', 'danger')
            finally:
                cursor.close()
                conn.close()
        else:
            flash('Tidak dapat terhubung ke database.', 'danger')

    return render_template('login.html')

# Route untuk logout
@app.route('/logout')
def logout():
    session.clear()
    flash('Anda telah berhasil logout.', 'success')
    return redirect(url_for('login'))

# Route untuk dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    tasks = []
    activities = []
    
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            
            # Mengambil tugas untuk user yang sedang login
            cursor.execute("""
                SELECT id, mata_kuliah, tugas, DATE_FORMAT(deadline, '%Y-%m-%d') as deadline 
                FROM tasks 
                WHERE user_id = %s 
                ORDER BY deadline ASC""", 
                (session['user_id'],))
            tasks = cursor.fetchall()
            
            # Mengambil kegiatan untuk user yang sedang login
            cursor.execute("""
                SELECT id, kegiatan, jenis_kegiatan, DATE_FORMAT(deadline, '%Y-%m-%d') as deadline 
                FROM activities 
                WHERE user_id = %s 
                ORDER BY deadline ASC""", 
                (session['user_id'],))
            activities = cursor.fetchall()
            
            cursor.close()
            conn.close()
        except Error as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')
            
    return render_template('dashboard.html', tasks=tasks, activities=activities)

# Route untuk menambah tugas
@app.route('/add_task', methods=['GET', 'POST'])
@login_required
def add_task():
    if request.method == 'POST':
        mata_kuliah = request.form.get('mata_kuliah')
        tugas = request.form.get('tugas')
        deadline = request.form.get('deadline')
        
        if not all([mata_kuliah, tugas, deadline]):
            flash('Mohon isi semua field.', 'danger')
            return render_template('add_task.html')
            
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO tasks (mata_kuliah, tugas, deadline, user_id) 
                    VALUES (%s, %s, %s, %s)""",
                    (mata_kuliah, tugas, deadline, session['user_id']))
                conn.commit()
                flash('Tugas berhasil ditambahkan!', 'success')
                return redirect(url_for('dashboard'))
            except Error as e:
                flash(f'Terjadi kesalahan: {str(e)}', 'danger')
            finally:
                cursor.close()
                conn.close()
                
    return render_template('add_task.html')

# Route untuk menambah kegiatan
@app.route('/add_activity', methods=['GET', 'POST'])
@login_required
def add_activity():
    if request.method == 'POST':
        kegiatan = request.form.get('kegiatan')
        jenis_kegiatan = request.form.get('jenis_kegiatan')
        deadline = request.form.get('deadline')
        
        if not all([kegiatan, jenis_kegiatan, deadline]):
            flash('Mohon isi semua field.', 'danger')
            return render_template('add_activity.html')
            
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO activities (kegiatan, jenis_kegiatan, deadline, user_id) 
                    VALUES (%s, %s, %s, %s)""",
                    (kegiatan, jenis_kegiatan, deadline, session['user_id']))
                conn.commit()
                flash('Kegiatan berhasil ditambahkan!', 'success')
                return redirect(url_for('dashboard'))
            except Error as e:
                flash(f'Terjadi kesalahan: {str(e)}', 'danger')
            finally:
                cursor.close()
                conn.close()
        else:
            flash('Tidak dapat terhubung ke database.', 'danger')
                
    return render_template('add_activity.html')

# Route untuk menghapus tugas
@app.route('/delete_task/<int:task_id>')
@login_required
def delete_task(task_id):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tasks WHERE id = %s AND user_id = %s", 
                         (task_id, session['user_id']))
            conn.commit()
            if cursor.rowcount > 0:
                flash('Tugas berhasil dihapus!', 'success')
            else:
                flash('Tugas tidak ditemukan.', 'danger')
        except Error as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()
    else:
        flash('Tidak dapat terhubung ke database.', 'danger')
        
    return redirect(url_for('dashboard'))

# Route untuk menghapus kegiatan
@app.route('/delete_activity/<int:activity_id>')
@login_required
def delete_activity(activity_id):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM activities WHERE id = %s AND user_id = %s", 
                         (activity_id, session['user_id']))
            conn.commit()
            if cursor.rowcount > 0:
                flash('Kegiatan berhasil dihapus!', 'success')
            else:
                flash('Kegiatan tidak ditemukan.', 'danger')
        except Error as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()
    else:
        flash('Tidak dapat terhubung ke database.', 'danger')
        
    return redirect(url_for('dashboard'))

# Route untuk edit tugas
@app.route('/edit_task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            
            if request.method == 'POST':
                mata_kuliah = request.form.get('mata_kuliah')
                tugas = request.form.get('tugas')
                deadline = request.form.get('deadline')
                
                if not all([mata_kuliah, tugas, deadline]):
                    flash('Mohon isi semua field.', 'danger')
                    return redirect(url_for('edit_task', task_id=task_id))
                
                cursor.execute("""
                    UPDATE tasks 
                    SET mata_kuliah = %s, tugas = %s, deadline = %s 
                    WHERE id = %s AND user_id = %s""",
                    (mata_kuliah, tugas, deadline, task_id, session['user_id']))
                conn.commit()
                
                if cursor.rowcount > 0:
                    flash('Tugas berhasil diperbarui!', 'success')
                    return redirect(url_for('dashboard'))
                else:
                    flash('Tugas tidak ditemukan.', 'danger')
                    return redirect(url_for('dashboard'))
            
            # GET request - tampilkan form edit
            cursor.execute("""
                SELECT id, mata_kuliah, tugas, DATE_FORMAT(deadline, '%Y-%m-%d') as deadline 
                FROM tasks 
                WHERE id = %s AND user_id = %s""",
                (task_id, session['user_id']))
            task = cursor.fetchone()
            
            if task:
                return render_template('edit_task.html', task=task)
            else:
                flash('Tugas tidak ditemukan.', 'danger')
                return redirect(url_for('dashboard'))
                
        except Error as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()
    else:
        flash('Tidak dapat terhubung ke database.', 'danger')
    
    return redirect(url_for('dashboard'))

# Route untuk edit kegiatan
@app.route('/edit_activity/<int:activity_id>', methods=['GET', 'POST'])
@login_required
def edit_activity(activity_id):
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            
            if request.method == 'POST':
                kegiatan = request.form.get('kegiatan')
                jenis_kegiatan = request.form.get('jenis_kegiatan')
                deadline = request.form.get('deadline')
                
                if not all([kegiatan, jenis_kegiatan, deadline]):
                    flash('Mohon isi semua field.', 'danger')
                    return redirect(url_for('edit_activity', activity_id=activity_id))
                
                cursor.execute("""
                    UPDATE activities 
                    SET kegiatan = %s, jenis_kegiatan = %s, deadline = %s 
                    WHERE id = %s AND user_id = %s""",
                    (kegiatan, jenis_kegiatan, deadline, activity_id, session['user_id']))
                conn.commit()
                
                if cursor.rowcount > 0:
                    flash('Kegiatan berhasil diperbarui!', 'success')
                    return redirect(url_for('dashboard'))
                else:
                    flash('Kegiatan tidak ditemukan.', 'danger')
                    return redirect(url_for('dashboard'))
            
            # GET request - tampilkan form edit
            cursor.execute("""
                SELECT id, kegiatan, jenis_kegiatan, DATE_FORMAT(deadline, '%Y-%m-%d') as deadline 
                FROM activities 
                WHERE id = %s AND user_id = %s""",
                (activity_id, session['user_id']))
            activity = cursor.fetchone()
            
            if activity:
                return render_template('edit_activity.html', activity=activity)
            else:
                flash('Kegiatan tidak ditemukan.', 'danger')
                return redirect(url_for('dashboard'))
                
        except Error as e:
            flash(f'Terjadi kesalahan: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()
    else:
        flash('Tidak dapat terhubung ke database.', 'danger')
    
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)