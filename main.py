# Config ===

servername = "mpyochats"
servericon = "https://github.com/fries-git/imagestorage/blob/main/saltychatsicon.webp?raw=true"
maxmessages = 500
maxlen = 500
adminusers = ["fries"]
port = 8080
# Config ===

#import network
# COMMENT THE ABOVE OUT IF NOT ON MICROCONTROLLER ^
from microdot import Microdot
from microdot.websocket import with_websocket
import json
import random
import time
import requests
app = Microdot()
commands = {}
readonlyusers = []
connections = []

with open('wifi.json', 'r') as file:
    # Parse the JSON file directly into a Python object
    wifi = json.load(file)

SSID = wifi.get("SSID")
PASSWORD = wifi.get("PASSWORD")

print(f"Connecting to WiFi network: {SSID} with password: {PASSWORD}")

# COMMENT EVERYTHING BETWEEN THESE TWO COMMENTS IF NOT ON MICROCONTROLLER v

#wifi = network.WLAN(network.STA_IF)
#wifi.active(True)
#wifi.connect(SSID, PASSWORD)

# COMMENT EVERYTHING BETWEEN THESE TWO COMMENTS IF NOT ON MICROCONTROLLER ^

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

async def checkandtrim(channel, ws):
    filename = f"{channel}.json"

    try:
        with open(filename, "r") as f:
            lines = []

            for line in f:
                lines.append(line)

                if len(lines) > maxmessages:
                    old = lines.pop(0)

                    try:
                        msg = json.loads(old)

                        await ws.send(json.dumps({
                            "cmd": "message_delete",
                            "id": msg.get("id"),
                            "channel": channel
                        }))

                    except:
                        pass

    except OSError:
        return

    with open(filename, "w") as f:
        for line in lines:
            f.write(line)

def is_user_online(username):
    return any(c.username == username for c in connections)

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

def getmessagefromid(id, channel):
    try:
        with open(f"{channel}.json", "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except Exception:
                    continue
                if msg.get("id") == id:
                    return msg

    except OSError as e:
        print(f"Error occurred while fetching message: {e}")

    return None

async def save_message(data, conn, wsconn):
    channel = data.get("channel")
    await checkandtrim(channel, wsconn)

    content = data.get("content", "")
    reply_to = data.get("reply_to")
    ping = data.get("ping", True)

    username = conn.username if conn and conn.username else "John Smith"
    message_obj = {
        "id": make_id(),
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

    try:
        with open(f"{channel}.json", "a") as f:
            f.write(json.dumps(message_obj))
            f.write("\n")
    except OSError:
        pass

    return message_obj

@command("status_set")
async def status_set(ws, data):
    conn = next((c for c in connections if c.ws == ws), None)
    if conn is None:
        return
    print(f"Status set: {data}")
    status = data.get("status")
    print(f"Status set by: {conn.username}")
    for conn in connections:
        await ws.send(json.dumps({
            "cmd": "status_set",
            "status": {
                "status": status,
            }
            }))
    pass

@command("server_info")
async def server_info(ws, data):
    await ws.send(json.dumps({
        "cmd": "server_info",
        "name": servername,
        "icon": servericon
        }))

@command("message_delete")
async def message_delete(ws, data):
    conn = next((c for c in connections if c.ws == ws), None)
    if conn is None:
        return

    userdeleting = conn.username
    channel = data.get("channel")
    message_id = data.get("id")

    message = getmessagefromid(message_id, channel)

    if message is None:
        return

    if userdeleting == message.get("user"):
        print(f"User {conn.username} is deleting a message")

        tempname = f"{channel}.tmp"

        with open(f"{channel}.json", "r") as src:
            with open(tempname, "w") as dst:
                for line in src:
                    try:
                        msg = json.loads(line)
                    except:
                        continue

                    if msg.get("id") != message_id:
                        dst.write(line)

        import os

        try:
            os.remove(f"{channel}.json")
        except OSError:
            pass

        os.rename(tempname, f"{channel}.json")

        dead = []

        for conn in connections:
            try:
                await conn.ws.send(json.dumps({
                    "cmd": "message_delete",
                    "id": message_id,
                    "channel": channel
                }))
            except Exception as e:
                print(e)
                dead.append(conn)

        for conn in dead:
            connections.remove(conn)

    else:
        print("User is not the owner of the message")
        await ws.send(json.dumps({
            "cmd": "error",
            "val": "You are not the owner of this message, and thus cannot delete it.",
            "src": "message_delete"
        }))

@command("auth")
async def auth(ws, data):
    conn = next((c for c in connections if c.ws == ws), None)
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
        await ws.send(json.dumps({
        "cmd": "auth_success",
        "val": "Authentication successful"
    }))
        conn.authenticated = True
    await ws.send(json.dumps(ready(response)))
    conn.user_id = response.get("id")
    conn.username = response.get("username")
    print(f"User authenticated: {conn.username}")
    await ws.send(json.dumps({
        "cmd": "user_roles_set",
        "user": conn.username,
        "roles": ["user"],
        "set": True
        }))
    usernamestore = conn.username
    for conn in connections:
        await conn.ws.send(json.dumps(connect(usernamestore)))

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

    messages = [None] * limit
    count = 0

    try:
        with open(f"{channel}.json", "r") as f:
            for line in f:
                try:
                    messages[count % limit] = json.loads(line)
                    count += 1
                except:
                    pass
    except OSError:
        pass

    if count < limit:
        messages = messages[:count]
    else:
        start = count % limit
        messages = messages[start:] + messages[:start]

    if isinstance(start, int):
        if start > 0:
            messages = messages[:-start]

    messages = messages[-limit:]

    await ws.send(json.dumps({
        "cmd": "messages_get",
        "channel": channel,
        "messages": messages
    }))

    print("getting messages")   

@command("users_list")
async def users_list(ws, data):
    users = get_users()
    await ws.send(json.dumps({
        "cmd": "users_list",
        "users": users
    }))
    print(f"Users: {users}")    

@command("users_online")
async def users_online(ws, data):
    users = get_users()
    await ws.send(json.dumps({
        "cmd": "users_list",
        "users": users
    }))
    print(f"Users: {users}") 

@command("message_new")
async def message_new(ws, data):
    print("Received new message")
    print(f"Data: {data}")
    content = data.get("content")
    print(f"Content: {content}")

    if len(content) >= maxlen:
        return await ws.send(json.dumps({
            "cmd": "error",
            "val": f"Message too long. Maximum length is {maxlen} characters.",
            "src": "message_new"
        }))

    conn = next((c for c in connections if c.ws == ws), None)
    username = conn.username if conn and conn.username else "John Smith"

    if content.startswith("!readmode "):
        if username not in adminusers:
            return await ws.send(json.dumps({
                "cmd": "error",
                "val": "You don't have permission to use this command.",
                "src": "message_new"
            }))

        target = content.split(maxsplit=1)[1].lower()

        if target in readonlyusers:
            readonlyusers.remove(target)
            msg = f"{target} is no longer in readonly mode."
        else:
            readonlyusers.append(target)
            msg = f"{target} is now in readonly mode."

        server_message = {
            "id": make_id(),
            "user": "server",
            "content": msg,
            "timestamp": time.time(),
            "type": "message",
            "pinned": False
        }

        dead = []

        for conn in connections:
            try:
                packet = {
                    "cmd": "message_new",
                    "message": {
                        **server_message,
                        "reply_to": None
                    },
                    "channel": data.get("channel"),
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

        return

    if username.lower() in readonlyusers:
        return await ws.send(json.dumps({
            "cmd": "error",
            "val": "You're in readonly mode right now! Please be more respectful next time.",
            "src": "message_new"
        }))

    message_obj = await save_message(data, conn, ws)
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

def connect(user):
    if user in adminusers:
        role = ["admin", "user"]
    else:  
        role = ["user"]
    return {
        "cmd": "user_connect",
        "user": {
            "username": user,
            "roles": role,
            "color": None
        }
    }

@app.route('/')
@with_websocket
async def echo(request, ws):
    conn = Connection(ws)
    try:
        connections.append(conn)
    except Exception as e:
        print(f"Error occurred while adding connection: {e}")

    await ws.send(json.dumps({
        "cmd": "server_update",
        "name": servername,
        "icon": servericon
    }))
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
                else:
                    print(f"Undefined/unimplemented command: {cmd}")
    finally:
        username = conn.username

        try:
            connections.remove(conn)
        except:
            pass

        if username and not is_user_online(username):
            print(f"{username} went fully offline")
            for c in connections:
                await c.ws.send(json.dumps({
                    "cmd": "user_leave",
                    "username": username
                }))

print(f"Server started on port {port}")
print(f"ws://localhost:{port}")
app.run(port=port)