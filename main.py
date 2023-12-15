import os
from zipfile import ZipFile
import tarfile
from flask import Flask, flash, request, redirect, url_for, render_template, send_from_directory
from markupsafe import escape
from werkzeug.utils import secure_filename
from flask import session
import sqlite3
from flask import g
import numpy as np
import datetime
import ReadImage
import imageio
import glob
import shutil


WINDOWS_SERVER_PATH = '/mnt/c/Users/jwoo/Desktop/HttpServer'
LINUX_PATH = '/home/junwoo'
UPLOAD_FOLDER = 'C:/Users/jwoo/Desktop/HttpServer/data'
SAVE_FOLDER = 'save'
MODEL_FOLDER = 'C:/Users/jwoo/Desktop/HttpServer/model'
DATABASE = 'C:/Users/jwoo/Desktop/HttpServer/fiona.db'
ALLOWED_EXTENSIONS = {'tif', 'trx', 'trxyt', 'nd2', 'czi', 'tiff'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 150 * 1000 * 1000 * 1000 * 1000
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'


def configure_setting(save_path, job_id, cutoff='8', post_processing='True') -> bool:
    with open(f'{save_path}/{job_id}/config.txt', 'w') as f:
        input_str = ''
        input_str += f'data = {WINDOWS_SERVER_PATH}/data/{job_id}\n'
        input_str += f'save_dir = {WINDOWS_SERVER_PATH}/save/{job_id}\n'
        input_str += f'model_dir = {LINUX_PATH}/HTC/model/histoneModel\n'
        input_str += f'cut_off = {cutoff}\n'
        input_str += f'all = False\n'
        input_str += f'makeImage = True\n'
        input_str += f'postProcessing = {post_processing}\n'

        input_str += '\n'
        input_str += 'immobile_cutoff = 5\n'
        input_str += 'hybrid_cutoff = 12\n'
        input_str += 'amp = 2\n'
        input_str += 'nChannel = 3\n'
        input_str += 'batch_size = 16\n'
        input_str += 'group_size = 160\n'
        f.write(input_str)
    return True


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[-1].lower() in ALLOWED_EXTENSIONS


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

    if 'username' in session:
        return render_template('hello.html', name=session["username"])

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
            os.mkdir(f'{SAVE_FOLDER}/{job_id}')
            if job_type == 'H2B':
                post_processing = 'True' if 'post_processing' in request.form else 'False'
                configure_setting(save_path=SAVE_FOLDER, job_id=job_id,
                                  cutoff=request.form['trajectory_length'],
                                  post_processing=post_processing)
        except Exception as e:
            print(e)
            print('Job_Id is already exist')
            return render_template('upload.html', job_exist=True)

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
        return render_template('upload.html', job_submission=True)
    job_id = None
    return render_template('upload.html')


@app.route('/upload/rad51', methods=['GET', 'POST'])
def rad51_classify():
    print('REQUEST: ', request)
    print('REQUEST FILE: ', request.files)
    print('REQUEST URL: ', request.url)
    print('REQUEST FORM: ', request.form)
    if request.method == 'POST':
        print('@@', request.form.get("erase"))
        print("##", request.form.get("job_id"))
        print("!!", request.files['filename'])
        if 'run_program' not in request.form:
            files = request.files.getlist('filename')
            for file in files:
                if not allowed_file(file.filename):
                    print('Not allowed file type: ', file.filename)
                    return redirect(request.url)

            try:
                received_file = request.files['filename']
                filename = secure_filename(received_file.filename)
                session['rad51_filename'] = filename
                received_file.save(f'./static/dummy/{filename}')
                if '.nd2' in filename:
                    reds, greens, transs, info = ReadImage.read_nd2(f'./static/dummy/{filename}')
                    static_urls = [f'dummy/{filename.split(".nd2")[0]}_red.gif',
                                   f'dummy/{filename.split(".nd2")[0]}_green.gif',
                                   f'dummy/{filename.split(".nd2")[0]}_trans.gif',
                                   f'dummy/{filename.split(".nd2")[0]}_all.gif'
                                   ]
                    imageio.mimsave(f'./static/{static_urls[0]}', reds, fps=2, loop=2)
                    imageio.mimsave(f'./static/{static_urls[1]}', greens, fps=2, loop=2)
                    imageio.mimsave(f'./static/{static_urls[2]}', transs, fps=2, loop=2)
                    imageio.mimsave(f'./static/{static_urls[3]}', reds + greens + transs, fps=2, loop=2)
                elif '.czi' in filename:
                    reds, greens, info = ReadImage.read_czi(f'./static/dummy/{filename}',
                                                            erase=request.form.get("erase"))
                    static_urls = [f'dummy/{filename.split(".czi")[0]}_red.gif',
                                   f'dummy/{filename.split(".czi")[0]}_green.gif',
                                   f'dummy/{filename.split(".czi")[0]}_all.gif'
                                   ]
                    imageio.mimsave(f'./static/{static_urls[0]}', reds, fps=3, loop=2)
                    imageio.mimsave(f'./static/{static_urls[1]}', greens, fps=3, loop=2)
                    imageio.mimsave(f'./static/{static_urls[2]}', reds + greens, fps=3, loop=2)
                elif '.tif' in filename or '.tiff' in filename:
                    reds, greens, info = ReadImage.read_tif(f'./static/dummy/{filename}')
                    static_urls = [f'dummy/{filename.split(".tif")[0]}_red.gif',
                                   f'dummy/{filename.split(".tif")[0]}_green.gif',
                                   f'dummy/{filename.split(".tif")[0]}_all.gif'
                                   ]
                    imageio.mimsave(f'./static/{static_urls[0]}', reds, fps=3, loop=2)
                    imageio.mimsave(f'./static/{static_urls[1]}', greens, fps=3, loop=2)
                    imageio.mimsave(f'./static/{static_urls[2]}', reds + greens, fps=3, loop=2)
                else:
                    return redirect(request.url)
                return render_template('rad51.html', erase=request.form.get("erase"),
                                       job_id=request.form.get("job_id"), filename=filename,
                                       score=request.form.get("score"),
                                       images=static_urls, len=len(static_urls), info=info)
            except Exception as e:
                print('Image create Err:', e)
                return redirect(request.url)

        if 'run_program' in request.form:
            if 'rad51_filename' not in session:
                return render_template('rad51.html', no_file=True)

            job_type = 'Rad51_protein'
            score = 90

            if len(request.form['job_id']) == 0:
                print('Input job id')
                return redirect(request.url)
            else:
                job_id = request.form['job_id']

            if 'score' in request.form:
                score = int(request.form.get('score'))
                if score < 0 or score > 100:
                    score = 90

            try:
                job_exist = query_db(f'SELECT COUNT() FROM job WHERE job_id = (?)', [job_id])
                os.mkdir(f'{UPLOAD_FOLDER}/{job_id}')
                os.mkdir(f'{SAVE_FOLDER}/{job_id}')
            except Exception as e:
                print(e)
                print('Job_Id is already exist')
                return render_template('rad51.html', job_exist=True)

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
                input_str += f'score = {str(score)}\n'
                input_str += f'erase = {False if request.form.get("erase") != "True" else True}'
                f.write(input_str)

            x = session['rad51_filename'].split('.')[0:-1]
            dummyname = ''
            for i in range(len(x)):
                dummyname += x[i]
            for dummy in os.scandir(f'./static/dummy'):
                if dummyname in dummy.path:
                    os.remove(dummy.path)
            session.pop('rad51_filename')
            return render_template('rad51.html', job_submission=True)
    job_id = None
    return render_template('rad51.html')


@app.route('/download', methods=['GET', 'POST'])
def download_file():
    if request.method == 'POST':
        if 'delete_job_id' in request.form:
            try:
                delete_job_id = request.form['delete_job_id'].strip().split('delete')[1].strip()
                query_db(f'DELETE FROM job WHERE job_id=(?)', [delete_job_id])
                query_db(f'COMMIT')
                shutil.rmtree(f'{UPLOAD_FOLDER}/{delete_job_id}', ignore_errors=True)
                shutil.rmtree(f'{SAVE_FOLDER}/{delete_job_id}', ignore_errors=True)
            except Exception as e:
                print(e)
                print('JOB delete ERR')

    if request.method == 'GET':
        with app.app_context():
            job_dict = dict()
            lens = dict()
            try:
                all_jobs = np.array(list(query_db(f"SELECT * FROM job WHERE user_name=(?)",
                                                  [session['username']])))[::-1]
                if len(all_jobs) == 0:
                    return render_template('download.html', jobs=None)

                ## maybe slower than resorting from the all_jobs rather than query for DB
                #finished_jobs = np.array(list(query_db(f"SELECT * FROM job WHERE user_name=(?) AND status=(?)",
                #                              [session['username'], 'finished'])))

                job_ids = all_jobs[:, 0]
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
        return render_template('download.html',
                               submit_job=True, all_jobs=all_jobs, files=job_dict, job_len=lens,
                               save_path=f'{SAVE_FOLDER}/', job_ids=job_ids)
    return redirect(request.url)


@app.route('/save/<job_id>/<filename>', methods=['GET'])
def download(job_id, filename):
    return send_from_directory(directory=f'{SAVE_FOLDER}/{job_id}', path=filename)


@app.route('/save/<job_id>', methods=['GET'])
def download_zip(job_id):
    files = os.listdir(f'{SAVE_FOLDER}/{job_id}')
    with tarfile.open(f'{SAVE_FOLDER}/{job_id}/{job_id}_all.tar', 'w:') as myzip:
        for file in files:
            if '.tar' not in file:
                myzip.add(f'{SAVE_FOLDER}/{job_id}/{file}', arcname=file)
    return send_from_directory(directory=f'{SAVE_FOLDER}/{job_id}', path=f'{job_id}_all.tar')


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
