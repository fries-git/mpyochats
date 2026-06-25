import os

def get_emojis():
    emojis = {}
    emoji_id = 1

    for filename in sorted(os.listdir("emojis")):
        if "." in filename:  # basic safety check
            name = filename.rsplit(".", 1)[0]
            emojis[str(emoji_id)] = {
                "name": name,
                "fileName": filename
            }

            emoji_id += 1

    return emojis

print(get_emojis())