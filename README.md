# mpyochats

A lightweight OChats server fork designed for the ESP32C6.

## What is Ochats?
Ochats is a lightweight (runs on anything both client and server wise as I'm proving), open source (all code is documented and easy to use with the intent of clients being easy to make), websocket based decentralized chat server.

## Setup
To setup the server, just create and edit the wifi and config.json.\
Create the file wifi.json and in it put {"SSID": "<wifiname>", "PASSWORD": "<password>"}\
Next, look at the config.json. Each channel is:\
```
{
      "name": "channel name",
      "type": "text", # Only supported format is text
      "description": "channel description",
      "permissions": {
        "view": ["user"],
        "send": ["admin"],
        "react": ["user"]
}
```
and these are all just stored in a json array. Quite simple really, just paste the above block in, modify it, and on the last } add a comma to the end if you intend to add another channel after it.
