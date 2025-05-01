import subprocess
from concurrent.futures import ThreadPoolExecutor

def list_crawler_containers(prefix="crawler_"):
    result = subprocess.run(
        ["docker", "ps", "-a", "--format", "{{.Names}}"],
        capture_output=True, text=True
    )
    names = result.stdout.strip().splitlines()
    return [name for name in names if name.startswith(prefix)]

def stop_and_remove(name):
    print(f"🛑 중지 및 제거: {name}")
    subprocess.run(["docker", "stop", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["docker", "rm", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"✅ 제거 완료: {name}")

if __name__ == "__main__":
    containers = list_crawler_containers()
    if not containers:
        print("✅ 중지할 crawler 컨테이너가 없습니다.")
    else:
        with ThreadPoolExecutor() as executor:
            executor.map(stop_and_remove, containers)
        print("✅ 모든 crawler 컨테이너 병렬 중지 및 제거 완료.")
