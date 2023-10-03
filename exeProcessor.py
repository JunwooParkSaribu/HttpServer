import subprocess
import sqlite3
import datetime
import numpy as np
import time
import queue
import os

DATA_FOLDER = 'C:/Users/jwoo/Desktop/HttpServer/data'
SAVE_FOLDER = 'C:/Users/jwoo/Desktop/HttpServer/save'
MODEL_PATH = 'C:/Users/jwoo/Desktop/HttpServer/model'
DATA_BASE = 'C:/Users/jwoo/Desktop/HttpServer/fiona.db'
SUBMITTIME_INDEX = -999


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
    return datetime.datetime.strptime(tuple[SUBMITTIME_INDEX], "%Y-%m-%d %H:%M:%S")


def run_command(cmd):
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return process


if __name__ == '__main__':
    NB_PROCESS = 2
    job_id_index = -999
    job_type_index = -999
    sleep_time = 30
    q_size = 10
    process_line = {}
    jobs = []
    job_queue = queue.Queue(maxsize=q_size)

    try:
        mydb = sqlite3.connect(DATA_BASE)
        cursor = mydb.cursor()
        cols = list(cursor.execute("SELECT c.name FROM pragma_table_info('job') c;"))
        for i, col in enumerate(cols):
            if 'submit_time' in col:
                SUBMITTIME_INDEX = i
            if 'job_id' in col:
                job_id_index = i
            if 'job_type' in col:
                job_type_index = i
        mydb.commit()
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
        print('Current running process:')
        for process in process_line:
            print(f'{process} : {process_line[process]}')
        print()

        """
        Update the finished job to DB.
        """
        for running_process in process_line:
            try:
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if running_process.poll() == 0:
                    print('Process finished for the job : ', process_line[running_process])
                    cursor.execute("UPDATE job SET status=?, end_time=? WHERE job_id=?;",
                                   ['finished', current_time, process_line[running_process]])
                    end_process.append(running_process)
                elif running_process.poll() == 1:
                    print('Process ERR(1): ', running_process)
                    cursor.execute("UPDATE job SET status=?, end_time=? WHERE job_id=?;",
                                   ['canceled', current_time, process_line[running_process]])
                    end_process.append(running_process)
            except Exception as e:
                print(e)
                print('ERR on running process (DB cursor ERR):',
                      process_line[running_process])
                exit(1)

        for finished_process in end_process:
            del process_line[finished_process]
        try:
            mydb.commit()
        except Exception as e:
            print(e)
            print('DB commit ERR')

        if len(process_line) < NB_PROCESS:
            try:
                next_job_id, next_job_type = job_queue.get(timeout=sleep_time)
            except Exception:
                continue

            try:
                # next_job_id is for the path of configuration file
                if next_job_type == 'H2B':
                    # ERR on mkdir is already checked on server script.
                    os.mkdir(f'{SAVE_FOLDER}/{next_job_id}')
                    if configure_setting(data_path=DATA_FOLDER, save_path=SAVE_FOLDER,
                                         model_path=MODEL_PATH, job_id=next_job_id):
                        proc = run_command(['./h2b_pipe.exe', f'{SAVE_FOLDER}/{next_job_id}'])

                elif next_job_type == 'Rad51':
                    # ERR on mkdir is already checked on server script.
                    os.mkdir(f'{SAVE_FOLDER}/{next_job_id}')
                    proc = run_command(['./rad51.exe', f'{next_job_id}'])

                elif next_job_type == 'Rad51_protein':
                    # ERR on mkdir is already checked on server script.
                    os.mkdir(f'{SAVE_FOLDER}/{next_job_id}')
                    proc = run_command(['./rad51_protein.exe', f'{next_job_id}'])

                cursor.execute("UPDATE job SET status=? WHERE job_id=?;", ['running', next_job_id])
                process_line[proc] = next_job_id
            except Exception as e:
                print(e)
                print('ERR job id:,', next_job_id)
                print('DB update for running stats ERROR')
                exit(1)
        else:
            time.sleep(sleep_time)
