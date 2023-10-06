import os
from flask import Flask, flash, request, redirect, url_for, render_template, send_from_directory
from markupsafe import escape
from werkzeug.utils import secure_filename
from flask import session
from PIL import Image as im
import sqlite3
from flask import g
import numpy as np
import datetime
import read_nd2
import imageio
import glob
import shutil


UPLOAD_FOLDER = 'C:/Users/jwoo/Desktop/HttpServer/data'
SAVE_FOLDER = './save'
MODEL_FOLDER = 'C:/Users/jwoo/Desktop/HttpServer/model'
DATABASE = 'C:/Users/jwoo/Desktop/HttpServer/fiona.db'
ALLOWED_EXTENSIONS = {'tif', 'trxyt', 'nd2'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 150 * 1000 * 1000 * 1000 * 1000
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
                query_db(f"INSERT INTO users (name, password) VALUES (?, ?)",
                         [request.form['username'], request.form['password']])
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
                password = request.form['password']
                # only for the name column in the DB
                user_exist = query_db(f'SELECT COUNT() FROM users WHERE name = (?) AND password = (?)',
                                      [username, password]).pop()[0]
                if user_exist == 0:
                    flash('Wrong user name or password')
                    error = 'Invalid credentials'
                    return render_template('hello.html', error=error)
                else:
                    session['username'] = username
            except Exception as e:
                print(e)
                print("Wrong user name or password")
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
        ### turn to rad51 page
        if 'rad51' in request.form:
            return redirect(url_for('rad51_classify'))

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
            return redirect(request.url)

        for file in files:
            if not allowed_file(file.filename):
                print('Not allowed file type: ', file.filename)
                return redirect(request.url)

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
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            query_db(f"INSERT INTO job (user_name, job_id, job_type, status, submit_time) VALUES (?, ?, ?, ?, ?)",
                     [session['username'], job_id, job_type, 'resources', current_time])
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


@app.route('/upload/rad51', methods=['GET', 'POST'])
def rad51_classify():
    print('REQUEST: ', request)
    print('REQUEST FILE: ', request.files)
    print('REQUEST URL: ', request.url)
    print('REQUEST FORM: ', request.form)
    if request.method == 'POST':
        if len(request.files) != 0:
            files = request.files.getlist('filename')
            for file in files:
                if not allowed_file(file.filename):
                    print('Not allowed file type: ', file.filename)
                    return redirect(request.url)

            try:
                print("@@@@@@@@@@@@@@@@@@@@")
                nd2_file = request.files['filename']
                filename = secure_filename(nd2_file.filename)
                session['rad51_filename'] = filename
                session['z_projection'] = request.form.get('z_projection')
                print(session['z_projection'])
                nd2_file.save(f'./static/dummy/{filename}')
                red, green, blue = read_nd2.read_nd2(f'./static/dummy/{filename}')

                static_urls = [f'dummy/{filename.split(".nd2")[0]}_red.png',
                               f'dummy/{filename.split(".nd2")[0]}_green.png',
                               f'dummy/{filename.split(".nd2")[0]}_trans.png'
                               ]

                imageio.imwrite(f'./static/{static_urls[0]}', red)
                imageio.imwrite(f'./static/{static_urls[1]}', green)
                imageio.imwrite(f'./static/{static_urls[2]}', blue)
                print('####################')

                return render_template('rad51.html', images=static_urls)
            except Exception as e:
                print('Image create Err:', e)
                return redirect(request.url)

        if 'run_program' in request.form:
            job_type = 'Rad51_protein'
            z_projection = session['z_projection']
            pixel_size = (15, 15)

            if 'job_id' not in request.form:
                print('Input job id')
                return redirect(request.url)

            if 'coord_data' in request.form:
                pixel_size = request.form.get('coord_data')
                pixel_size = (int(pixel_size.split(',')[0]), int(pixel_size.split(',')[1]))
            job_id = request.form['job_id']

            try:
                job_exist = query_db(f'SELECT COUNT() FROM job WHERE job_id = (?)', [job_id])
                os.mkdir(f'{UPLOAD_FOLDER}/{job_id}')
            except Exception as e:
                print(e)
                print('Job_Id is already exist')
                return redirect(request.url)

            try:
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                query_db(f"INSERT INTO job (user_name, job_id, job_type, status, submit_time) VALUES (?, ?, ?, ?, ?)",
                         [session['username'], job_id, job_type, 'resources', current_time])
                query_db(f'COMMIT')
            except Exception as e:
                print(e)
                print('Job insertion or commit ERR')
                return redirect(request.url)

            shutil.copy2(f'./static/dummy/{session["rad51_filename"]}', f'{UPLOAD_FOLDER}/{job_id}')
            with open(f'{UPLOAD_FOLDER}/{job_id}/config.txt', 'w') as f:
                input_str = ''
                input_str += f'data = {UPLOAD_FOLDER}/{job_id}/{session["rad51_filename"]}\n'
                input_str += f'save_dir = {SAVE_FOLDER}/{job_id}\n'
                input_str += f'model_dir = {MODEL_FOLDER}/model_rad51_protein\n'
                input_str += f'pixel_size = {str(min(pixel_size))}\n'
                input_str += f'z_projection = {z_projection}'
                f.write(input_str)

            for dummy in os.scandir(f'./static/dummy'):
                os.remove(dummy.path)
    job_id = None
    return render_template('rad51.html')


@app.route('/download')
def download_file():
    if request.method == 'GET':
        with app.app_context():
            job_dict = dict()
            job_ids = ''
            lens = dict()
            try:
                all_jobs = np.array(list(query_db(f"SELECT * FROM job WHERE user_name=(?)",
                                              [session['username']])))
                if len(all_jobs) == 0:
                    return render_template('download.html', jobs=None)

                ## maybe slower than resorting from the all_jobs rather than query for DB
                finished_jobs = np.array(list(query_db(f"SELECT * FROM job WHERE user_name=(?) AND status=(?)",
                                              [session['username'], 'finished'])))
                if len(finished_jobs) != 0:
                    job_ids = finished_jobs[:, 0]
                    for job_id in job_ids:
                        href_path = []
                        files = os.listdir(f'{SAVE_FOLDER}/{job_id}')
                        for file in files:
                            href_path.append(f'{SAVE_FOLDER}/{job_id}/{file}')
                        job_dict[job_id] = [files, href_path.copy()]
                        lens[job_id] = len(href_path)
            except Exception as e:
                print(e)
                print('JOB fetching ERR')
                return render_template('download.html', jobs=None)
        return render_template('download.html', submit_job=True, all_jobs=all_jobs,
                               finished_jobs=job_ids, files=job_dict, len=lens)
    return redirect(request.url)


@app.route('/save/<job_id>/<filename>', methods=['GET', 'POST'])
def download(job_id, filename):
    return send_from_directory(directory=f'{SAVE_FOLDER}/{job_id}', path=filename)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
