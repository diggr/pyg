import re
import os

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


def get_channel_files(CF):
    channels = []
    channel_dir = os.path.join(CF["PROJECT_DIR"], "channels")
    for group_name in os.listdir(channel_dir):
        group_dir = os.path.join(channel_dir, group_name)
        #ignore prov and update files
        for filename in os.listdir(group_dir):
            if ".prov" not in filename and "_2" not in filename:
                archive_filepath = os.path.join(group_dir, filename) 
                channels.append({
                    "archive": archive_filepath,
                    "archive_name": filename,
                    "group": group_name
                })
    return channels    

def get_video_files(CF):
    archives = []
    videos_dir = os.path.join(CF["PROJECT_DIR"], "videos")
    #ignore prov and update files
    for filename in os.listdir(videos_dir):
        if ".prov" not in filename and "_2" not in filename:
            archive_filepath = os.path.join(videos_dir, filename) 
            archives.append({
                "archive": archive_filepath,
                "archive_name": filename,
                "group": filename.replace(".zip", "")
            })
    return archives        