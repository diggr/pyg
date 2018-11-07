import re

def get_channel_id(youtube, user_name):
    """
    Looks up user id for ::user_name:: on the youtube api 
    """
    meta = youtube.channels().list(
        part="id,snippet",
        forUsername=user_name,
    ).execute()  
    try:
        return meta["items"][0]["id"]
    except:
        print("user name <{}> not found".format(user_name))
        return None


def remove_html(text):
    """
    Removes html tags from text
    """
    return re.sub('<[^<]+?>', '', text)        