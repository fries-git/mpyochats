# mpyochats

A lightweight OChats server fork designed for the ESP32C6.\

## What is Ochats?
Ochats is a lightweight (runs on anything both client and server wise as I'm proving), open source (all code is documented and easy to use with the intent of clients being easy to make), websocket based decentralized chat server.

## Is there AI Code?
As of now some code was ai generated during development but got completely rewritten. The only thing left AI is the demo client as I'm trying to just show something that works server side. The client is not the part that's really the project.

## Is there code that's not mine?
Yes. Microdot is a small websocket library used for this project.

## Setup
- Note that steps that say (CPY) or for Cpython, or what you would run on a windows computer, (MPY) is micropython, or what you'd run on an esp32 or rpiw, and if unlabeled assume the step is for both.
First, setup CPython or Micropython depending on how you want to run it. I've used `3.13` for Cpython, and Micropython 1.28 (I believe) for ESP32C6 throughout development.
(CPY) Next use `pip install -r requirements.txt`, or whatever you need for venv's/python versions, to get packages.
(MPY) All packages you need are base system packages, or bundled in (microdot)
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
and these are all just stored in a json array. Quite simple really, just paste the above block in, modify it, and on the last } add a comma to the end if you intend to add another channel after it.\
Once this is done, either run the Python file like you would any other Cpython file, or flash it to your microcontroller and run it that way.
