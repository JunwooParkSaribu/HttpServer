import os
from flask import Flask, flash, request, redirect, url_for, render_template, send_from_directory
from markupsafe import escape
from werkzeug.utils import secure_filename
from flask import session
import sqlite3
from flask import g


UPLOAD_FOLDER = './data'
SAVE_FOLDER = './save'
DATABASE = './users.db'
ALLOWED_EXTENSIONS = {'txt', 'py', 'html', 'trxyt'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 150 * 1000 * 1000
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

@app.route('/create_account', methods=['GET', 'POST'])
def create_account():
    if request.method == 'POST':
        with app.app_context():
            try:
                query_db(f"INSERT INTO users (name) VALUES (?)", [request.form['username']])
                query_db(f'COMMIT')
            except Exception as e:
                print(e)
                print('user is already exist')
                return render_template('create_account.html', err=request.form['username'])
            session['username'] = request.form['username']
        return redirect(url_for('index'))
    return render_template('create_account.html')

@app.route('/', methods=['GET', 'POST'])
def index():
    with app.app_context():
        print(query_db(f'SELECT * FROM users'))

    if request.method == 'POST':
        if 'logout' in request.form:
            session.pop('username', None)
            return redirect(url_for('index'))
        if 'upload' in request.form:
            return redirect(url_for('upload_files'))
        if 'create_account' in request.form:
            return redirect(url_for('create_account'))
        if 'download' in request.form:
            return redirect(url_for('download_file'))

        if 'login' in request.form:
            try:
                username = request.form['username']
                # only for the name column in the DB
                user_exist = query_db(f'SELECT COUNT() FROM users WHERE name = (?)', [username]).pop()[0]
                if user_exist == 0:
                    return render_template('hello.html', no_user=username)
                else:
                    session['username'] = username
            except Exception as e:
                print(e)
                print("user name not exist")
                return redirect(url_for('index'))

        if 'username' in session:
            print(f'Logged in as {session["username"]}')
            return render_template('hello.html', name=session["username"])
        else:
            return redirect(url_for('index'))

    elif request.method == 'GET':
        pass
    return render_template('hello.html')


@app.route('/upload', methods=['GET', 'POST'])
def upload_files():
    print('REQUEST: ', request)
    print('REQUEST FILE: ', request.files)
    print('REQUEST URL: ', request.url)
    job_type = ''
    if request.method == 'POST':
        if 'filename' not in request.files:
            print('No file part')
            return redirect(request.url)
        files = request.files.getlist('filename')
        if files[0].filename == '':
            print('No selected file')
            return redirect(request.url)

        try:
            job_type = request.form['job_type']
        except Exception as e:
            print(e)
            print('No job type selected')

        job_id = request.form['job_id']
        if job_id == '':
            return redirect(request.url)
        try:
            job_exist = query_db(f'SELECT COUNT() FROM job WHERE job_id = (?)', [job_id])
            os.mkdir(f'{UPLOAD_FOLDER}/{job_id}')
        except Exception as e:
            print(e)
            print('Job_Id is already exist')
            return redirect(request.url)

        try:
            query_db(f"INSERT INTO job (user_name, job_id, job_type, status) VALUES (?, ?, ?, ?)",
                     [session['username'], job_id, job_type, 'resources'])
            query_db(f'COMMIT')
        except Exception as e:
            print(e)
            print('Job insertion or commit ERR')
            return redirect(request.url)

        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(f'{UPLOAD_FOLDER}/{job_id}', filename))
                print(file)
            else:
                print('Not allowed file type', file)
    job_id = None
    return render_template('upload.html')

@app.route('/download')
def download_file():
    if request.method == 'GET':
        with app.app_context():
            try:
                jobs = query_db(f"SELECT * FROM job WHERE user_name=(?)",
                                [session['username']])
                job_id = jobs[3]
                print('loaded jobs:', jobs)
            except Exception as e:
                print(e)
                print('JOB fetching ERR')
                return render_template('download.html', jobs=None)

        #return render_template('download.html', jobs=jobs)
        return send_from_directory(f'{SAVE_FOLDER}/{job_id}')
    return redirect(request.url)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
