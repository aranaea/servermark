import re
import subprocess
from collections import defaultdict, namedtuple
from datetime import datetime
from enum import auto, Enum
from time import sleep

import requests
from ascii_graph import Pyasciigraph


class ServerType(Enum):
    daphne = auto()
    direct = auto()
    gunicorn = auto()
    hypercorn = auto()
    uvicorn = auto()
    uwsgi = auto()


Server = namedtuple("Server", ["module", "server_type", "settings"])

SERVERS = {
    # "aiohttp": Server("aiohttp_server", ServerType.direct, []),
    # "aiohttp-gunicorn-uvloop": Server(
    #     "aiohttp_server", ServerType.gunicorn, ["--worker-class", "aiohttp.worker.GunicornUVLoopWebWorker"]
    # ),
    # 'fastapi': Server('fastapi_server', ServerType.uvicorn, []),
    # "flask": Server("flask_server", ServerType.direct, []),
    # "flask-gunicorn-eventlet": Server("flask_server", ServerType.gunicorn, ["--worker-class", "eventlet"]),
    # "flask-gunicorn-gevent": Server("flask_server", ServerType.gunicorn, ["--worker-class", "gevent"]),
    # "flask-uwsgi-4threads-4proc": Server(
    #     "flask_server", ServerType.uwsgi, ["-s", "0.0.0.0:5000", "--threads", "4", "--process", "4"]
    # ),
    # "flask-uwsgi-4threads-4workers": Server(
    #     "flask_server", ServerType.uwsgi, ["-s", "0.0.0.0:5000", "--threads", "4", "--workers", "4"]
    # ),
    # "flask-uwsgi": Server("flask_server", ServerType.uwsgi, ["-s", "0.0.0.0:5000"]),
    # "flask-gunicorn-meinheld": Server(
    #     "flask_server", ServerType.gunicorn, ["--worker-class", "meinheld.gmeinheld.MeinheldWorker"]
    # ),
    # "blacksheep-daphne": Server("blacksheep_server", ServerType.daphne, []),
    "blacksheep-hypercorn": Server("blacksheep_server", ServerType.hypercorn, []),
    "blacksheep-uvicorn": Server("blacksheep_server", ServerType.uvicorn, []),
    "quart": Server("quart_server", ServerType.direct, []),
    "quart-daphne": Server("quart_server", ServerType.daphne, []),
    "quart-hypercorn": Server("quart_server", ServerType.hypercorn, ["--worker-class", "uvloop"]),
    # "quart-trio": Server("quart_trio_server", ServerType.hypercorn, ["--worker-class", "trio"]),
    "quart-uvicorn": Server("quart_server", ServerType.uvicorn, []),
    # "sanic": Server("sanic_server", ServerType.direct, []),
    # "sanic-gunicorn-uvloop": Server(
    #     "sanic_server", ServerType.gunicorn, ["--worker-class", "sanic.worker.GunicornWorker"]
    # ),
    # "sanic-daphne": Server(
    #     "sanic_server", ServerType.daphne, []
    # ),
    # "sanic-uvicorn": Server(
    #     "sanic_server", ServerType.uvicorn, []
    # ),
    # "sanic-hypercorn": Server(
    #     "sanic_server", ServerType.hypercorn, []
    # ),

    # "starlette": Server("starlette_server", ServerType.uvicorn, []),
}

REQUESTS_SECOND_RE = re.compile(r"Requests\/sec\:\s*(?P<reqsec>\d+\.\d+)(?P<unit>[kMG])?")
UNITS = {
    "k": 1_000,
    "M": 1_000_000,
    "G": 1_000_000_000,
}
HOST = "127.0.0.1"
PORT = 5000


def run_server(server):
    if server.server_type == ServerType.gunicorn:
        print("gunicorn", "{}:app".format(server.module), "-b", "{}:{}".format(HOST, PORT))
        return subprocess.Popen(
            ["gunicorn", "{}:app".format(server.module), "-b", "{}:{}".format(HOST, PORT)] + server.settings,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd="servers",
        )
    elif server.server_type == ServerType.uvicorn:
        print("uvicorn", "{}:app".format(server.module), "--host", HOST, "--port", str(PORT), "--no-access-log")
        return subprocess.Popen(
            ["uvicorn", "{}:app".format(server.module), "--host", HOST, "--port", str(PORT), "--no-access-log"]
            + server.settings,
            cwd="servers",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    elif server.server_type == ServerType.daphne:
        print("daphne", "{}:app".format(server.module), "-b", HOST, "-p", str(PORT))
        return subprocess.Popen(
            ["daphne", "{}:app".format(server.module), "-b", HOST, "-p", str(PORT)] + server.settings,
            cwd="servers",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    elif server.server_type == ServerType.hypercorn:
        print("hypercorn", "{}:app".format(server.module), "-b", "{}:{}".format(HOST, PORT))
        return subprocess.Popen(
            ["hypercorn", "{}:app".format(server.module), "-b", "{}:{}".format(HOST, PORT)] + server.settings,
            cwd="servers",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    elif server.server_type == ServerType.direct:
        return subprocess.Popen(
            ["python", "{}.py".format(server.module)] + server.settings,
            cwd="servers",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    elif server.server_type == ServerType.uwsgi:
        return subprocess.Popen(
            ["uwsgi", "--protocol=http", "-w", "{}:app".format(server.module)] + server.settings,
            cwd="servers",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        raise ValueError("Unknown server {}".format(server))


def test_server(server):
    response = requests.get("http://{}:{}/tracks/".format(HOST, PORT))
    assert response.status_code == 200
    # assert server.module in response.text
    assert 'store_tracks' in response.json()
    response = requests.post("http://{}:{}/tracks".format(HOST, PORT), json={"camera_tracks": [1, 2, 3]})
    assert response.status_code == 200
    assert 'cam_track_count' in response.json()
    # assert server.module in response.text


def run_benchmark(path, script=None):
    if script is not None:
        script_cmd = "-s {}".format(script)
    else:
        script_cmd = ""
    output = subprocess.check_output(
        "wrk -c 32 -d 60s {} http://{}:{}/{}".format(script_cmd, HOST, PORT, path), shell=True,
    )
    match = REQUESTS_SECOND_RE.search(output.decode())
    requests_second = float(match.group("reqsec"))
    if match.group("unit"):
        requests_second = requests_second * UNITS[match.group("unit")]
    return requests_second


if __name__ == "__main__":
    results = defaultdict(list)
    for name, server in SERVERS.items():
        try:
            print("Testing {} {}".format(name, datetime.now().isoformat()))
            process = run_server(server)
            sleep(5)
            test_server(server)
            results["get"].append((name, run_benchmark("tracks")))
            results["post"].append((name, run_benchmark("tracks", "scripts/big_post.lua")))
        finally:
            process.terminate()
            process.wait()
    graph = Pyasciigraph()
    for key, value in results.items():
        for line in graph.graph("{} requests/second".format(key), sorted(value, key=lambda result: result[1])):
            print(line)
