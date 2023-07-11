import subprocess
import sqlite3
import datetime
import numpy as np
import time
import queue
import os

DATA_FOLDER = 'C:/Users/jwoo/Desktop/HTCserver/data'
SAVE_FOLDER = 'C:/Users/jwoo/Desktop/HTCserver/save'
MODEL_PATH = 'C:/Users/jwoo/Desktop/HTCserver/model'
DATA_BASE = 'C:/Users/jwoo/Desktop/HTCserver/users.db'
TIMESTAMP_INDEX = -999


def configure_setting(data_path, save_path, model_path, job_id) -> bool:
    with open(f'{save_path}/{job_id}/config.txt', 'w') as f:
        input_str = ''
        input_str += f'data = {data_path}/{job_id}\n'
        input_str += f'save_dir = {save_path}/{job_id}\n'
        input_str += f'model_dir = {model_path}/model_htc\n'
        input_str += f'cut_off = 8\n'
        input_str += f'all = False\n'
        input_str += f'makeImage = True\n'
        input_str += f'postProcessing = True\n'

        input_str += '\n'
        input_str += 'immobile_cutoff = 5\n'
        input_str += 'hybrid_cutoff = 12\n'
        input_str += 'amp = 2\n'
        input_str += 'nChannel = 3\n'
        input_str += 'batch_size = 16\n'
        input_str += 'group_size = 160\n'
        f.write(input_str)
    return True


def get_date_from_tuple(tuple):
    return datetime.datetime.strptime(tuple[TIMESTAMP_INDEX], "%Y-%m-%d %H:%M:%S")


def run_command(cmd):
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return process


if __name__ == '__main__':
    NB_PROCESS = 2
    job_id_index = -999
    job_type_index = -999
    process_line = {}
    jobs = []
    job_queue = queue.Queue(maxsize=10)

    try:
        mydb = sqlite3.connect(DATA_BASE)
        cursor = mydb.cursor()
        cols = list(cursor.execute("SELECT c.name FROM pragma_table_info('job') c;"))
        for i, col in enumerate(cols):
            if 'Timestamp' in col:
                TIMESTAMP_INDEX = i
            if 'job_id' in col:
                job_id_index = i
            if 'job_type' in col:
                job_type_index = i
        cursor.close()
    except Exception as e:
        print(e)
        print("Sqlite connection ERR")
        exit(1)

    while True:
        end_process = []
        try:
            """
            Get job list from DB and insert into queue
            """
            mydb.commit()
            cursor = mydb.cursor()
            jobs = list(cursor.execute("SELECT * FROM job WHERE status=?;", ['resources']))
            if len(jobs) != 0:
                jobs = np.array(sorted(jobs, key=get_date_from_tuple))
                job_sequence = jobs[:, (job_id_index, job_type_index)]
                for job in job_sequence:
                    job_queue.put(job)
                    job_id = job[0]
                    cursor.execute("UPDATE job SET status=? WHERE job_id=?;", ['pending', job_id])
        except Exception as e:
            print(e)
            print('ERR on job queueing')

        print('Queue size: ', job_queue.qsize())
        print(process_line)

        """
        Update the finished job to DB.
        """
        for running_process in process_line:
            if running_process.poll() == 0:
                print('Process completed: ', running_process)
                try:
                    cursor.execute("UPDATE job SET status=? WHERE job_id=?;",
                                   ['finished', process_line[running_process]])
                except Exception as e:
                    print(e)
                    print('ERR job id:,', process_line[running_process])
                    print('DB update for finished stats ERROR')
                    exit(1)
                end_process.append(running_process)
        for finished_process in end_process:
            del process_line[finished_process]

        if len(process_line) < NB_PROCESS:
            try:
                next_job_id, next_job_type = job_queue.get(timeout=5)
            except Exception:
                print("No job is waiting...")
                continue

            if next_job_type == 'HTC':
                # ERR on mkdir is already checked on server script.
                os.mkdir(f'{SAVE_FOLDER}/{next_job_id}')
                if configure_setting(data_path=DATA_FOLDER, save_path=SAVE_FOLDER,
                                     model_path=MODEL_PATH, job_id=next_job_id):
                    proc = run_command(['./h2b_pipe.exe', f'{SAVE_FOLDER}/{next_job_id}'])

            try:
                cursor.execute("UPDATE job SET status=? WHERE job_id=?;", ['running', next_job_id])
                process_line[proc] = next_job_id
            except Exception as e:
                print(e)
                print('ERR job id:,', next_job_id)
                print('DB update for running stats ERROR')
                exit(1)
        else:
            time.sleep(10)
