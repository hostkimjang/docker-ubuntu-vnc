import subprocess
from subprocess import Popen

def list_containers_with_ids(prefix="crawler_"):
    output = subprocess.check_output(["docker", "ps", "--format", "{{.ID}} {{.Names}}"]).decode()
    containers = []
    for line in output.strip().splitlines():
        container_id, name = line.split(maxsplit=1)
        if name.startswith(prefix):
            containers.append((container_id, name))
    return containers

def stream_logs(container_id, name):
    print(f"\n📦 Streaming logs for {name} ({container_id}):\n{'='*50}")
    return Popen(["docker", "logs", "-f", container_id])

containers = list_containers_with_ids()
procs = [stream_logs(cid, name) for cid, name in containers]

for p in procs:
    p.wait()
