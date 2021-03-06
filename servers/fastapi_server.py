from fastapi import FastAPI, Form

app = FastAPI()


@app.get("/")
@app.get("/{number:int}")
async def index(number):
    return "{}-fib({})={}".format(__file__, number, _fib(int(number)))


@app.post('/')
async def post(fib: int = Form(...)):
    return "{}-fib({})={}".format(__file__, fib, _fib(int(fib)))


@app.get("/ping/")
async def ping():
    return {"Ping": "Pong"}


def _fib(n):
    if n == 0:
        return 0
    elif n == 1:
        return 1
    else:
        return _fib(n - 1) + _fib(n - 2)
