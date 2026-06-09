import uuid

from microdot import Microdot
from microdot.websocket import with_websocket
import json
import random
import time

import requests

app = Microdot()
commands = {}

connections = []

def make_id():
    return "%08x%08x" % (random.getrandbits(32), random.getrandbits(32))

class Connection:
    def __init__(self, ws):
        self.ws = ws
        self.user_id = None
        self.username = None
        self.authenticated = False

def generatevalidationdata():
    return {
        "cmd": "handshake",
        "val": {
            "server": "mpyochats",
            "limits": {},
            "version": "1.0.1",
            "validator_key": "mpyochats"
        }
    }

def ready(obj):
    return {
        "cmd": "ready",
        "user": obj
    }

def command(name):
    def wrapper(fn):
        commands[name] = fn
        return fn
    return wrapper

def channelbreak(mode=1):
    try:
        with open("config.json", "r") as file:
            config = json.load(file)
        channels = config.get("channels", [])
        if mode == 1:
            return channels
        else:
            for channel in channels:
                print(channel)
            return None
    except Exception as e:
        print(f"Error reading config: {e}")
        return []

def save_message(data, conn):
    channel = data.get("channel")
    thread_id = data.get("thread_id")
    content = data.get("content", "")
    reply_to = data.get("reply_to")
    ping = data.get("ping", True)

    username = conn.username if conn and conn.username else "John Smith"

    message_obj = {
        "id": str(uuid.uuid4()),
        "user": username,
        "content": content,
        "timestamp": time.time(),
        "type": "message",
        "pinned": False
    }

    if reply_to:
        message_obj["reply_to"] = {
            "id": reply_to,
            "user": "unknown"
        }
        message_obj["ping"] = ping

    target_file = f"{channel}.json" if channel else None

    if target_file:
        try:
            with open(target_file, "r") as f:
                raw = f.read().strip()
                messages = json.loads(raw) if raw else []
                if not isinstance(messages, list):
                    messages = []
        except OSError:
            messages = []

        messages.append(message_obj)

        with open(target_file, "w") as f:
            json.dump(messages, f)

    return message_obj


@command("auth")
async def auth(ws, data):
    print(f"Received auth data: {data}")
    conn = next((c for c in connections if c.ws == ws), None)
    print(f"Received validator: {data.get('validator')}")
    if conn is None:
        return
    link = f"https://social.rotur.dev/validate?v={data.get('validator')}&key=mpyochats"
    response = (requests.get(link)).json()
    if not response.get("valid", False):
        print("Failed to validate user")
        await ws.send(json.dumps({
        "cmd": "auth_error",
        "val": "You gotta be fucked up if you think I know."
    }))
        conn.authenticated = False
        return
        
    else:
        print("User validated successfully")
        print(response)
        await ws.send(json.dumps({
        "cmd": "auth_success",
        "val": "Authentication successful"
    }))
        conn.authenticated = True
    await ws.send(json.dumps(ready(response)))
    conn.user_id = response.get("id")
    conn.username = response.get("username")
    print(f"User authenticated: {conn.user_id} or {conn.username}")
    

@command("messages_get")
async def messages_get(ws, data):
    channel = data.get("channel")
    start = data.get("start", 0)
    limit = data.get("limit", 100)

    if not channel:
        await ws.send(json.dumps({
            "cmd": "error",
            "val": "Invalid channel name"
        }))
        return

    limit = max(1, min(200, int(limit)))

    filename = f"{channel}.json"

    try:
        with open(filename, "r") as f:
            raw = f.read().strip()
            messages = json.loads(raw) if raw else []
    except OSError:
        messages = []

    if not isinstance(messages, list):
        messages = []

    messages.sort(key=lambda m: m.get("timestamp", 0))

    if isinstance(start, int):
        if start > 0:
            messages = messages[:-start]
    else:
        pass

    messages = messages[-limit:]

    await ws.send(json.dumps({
        "cmd": "messages_get",
        "channel": channel,
        "messages": messages
    }))
    print("getting messages")

@command("message_new")
async def message_new(ws, data):
    print("Received new message")
    print(data)

    conn = next((c for c in connections if c.ws == ws), None)
    message_obj = save_message(data, conn)
    channelstore = data.get("channel")
    dead = []
    for conn in connections:
        try:
            packet = {
                "cmd": "message_new",
                "message": {
                    **message_obj,
                    "reply_to": None
                },
                "channel": channelstore,
                "thread_id": None,
                "global": True
            }
            await conn.ws.send(json.dumps(packet))
        except Exception as e:
            print(e)
            dead.append(conn)

    for conn in dead:
        try:
            connections.remove(conn)
        except Exception as e:
            print("cleanup failed:", e)

@command("channels_get")
async def channels_get(ws, data):
    channels = channelbreak(1)
    print("getting channels")
    await ws.send(json.dumps({
        "cmd": "channels_get",
        "val": channels
    }))
    print(json.dumps({
        "cmd": "channels_get",
        "val": channels
    }))

def get_users():
    for c in connections:
        print(c.username)

    return [
        {
            "user_id": c.user_id,
            "username": c.username,
            "authenticated": c.authenticated
        }
        for c in connections
    ]

@app.route('/')
@with_websocket
async def echo(request, ws):
    conn = Connection(ws)
    connections.append(conn)

    await ws.send(json.dumps(generatevalidationdata()))
    try:
        while True:
            message = await ws.receive()
            if message is None:
                break
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                continue

            if isinstance(data, dict):
                cmd = data.get("cmd")
                if cmd in commands:
                    await commands[cmd](ws, data)
    finally:
        try:
            connections.remove(conn)
        except:
            pass

ported = 8080
print(f"Server started on port {ported}")
print(f"ws://localhost:{ported}")
app.run(port=ported)