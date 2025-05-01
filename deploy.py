import sqlite3
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor

CONTAINER_COUNT = 1
DB_PATH = "./app/food_data.db"

def get_total_records():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM restaurants")
    total = cur.fetchone()[0]
    conn.close()
    return total

def create_env_file(start, end, vnc_port, novnc_port, index):
    env_content = f"""\
START_INDEX={start}
END_INDEX={end}
VNC_PORT={vnc_port}
NOVNC_PORT={novnc_port}
CONTAINER_ID={index}
"""
    env_path = f".env.{index}"
    with open(env_path, "w") as f:
        f.write(env_content)
    return env_path

def run_container(index, start, end, vnc_port, novnc_port):
    print(f"🛠️ Container {index}: {start} ~ {end} (VNC: {vnc_port}, NoVNC: {novnc_port})")
    create_env_file(start, end, vnc_port, novnc_port, index)
    project_name = f"crawler_{index}"
    subprocess.run([
        "docker-compose",
        "--env-file", f".env.{index}",
        "-f", "docker-compose.yml",
        "-p", project_name,
        "up", "-d", "--build"
    ], check=True)
    print(f"🚀 Container {index} started successfully.")

def main():
    total = get_total_records()
    chunk = total // CONTAINER_COUNT

    with ThreadPoolExecutor(max_workers=CONTAINER_COUNT) as executor:
        for i in range(CONTAINER_COUNT):
            start = i * chunk
            end = (i + 1) * chunk if i != CONTAINER_COUNT - 1 else total
            vnc_port = 5901 + i
            novnc_port = 6080 + i
            executor.submit(run_container, i, start, end, vnc_port, novnc_port)

if __name__ == "__main__":
    print("🚀 병렬 Docker 컨테이너 배포 시작...")
    main()