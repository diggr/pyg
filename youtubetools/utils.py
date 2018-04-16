
def get_channel_id(youtube, user_name):
    meta = youtube.channels().list(
        part="id,snippet",
        forUsername=user_name,
    ).execute()  
    try:
        return meta["items"][0]["id"]
    except:
        print("user name <{}> not found".format(user_name))
        return None