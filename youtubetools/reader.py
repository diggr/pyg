"""
Reader for scraped youtube channels
Uses two classes: ChannelReader and Video


class ChannelReader properties:
- videos [list of Video objects]

- video_tags()
- video_categories()
- videos_by_tag()
- videos_by_category()


Video properities:
- id
- title
- description
- pub_date
- tags [list]
- categories [list]
- comments [list]

- comment_stats()
- users()


Use:

yt = ChannelReader("<channel name>")
for video in yt.videos:
    print(video.title)
    #...

"""

import json
import os
import re
from tqdm import tqdm
from collections import Counter, defaultdict
from .config import load_config
import zipfile

# directories
DATA_DIR = "data"
VIDEO_METADATA_DIR = "video_meta"
VIDEO_CAPTIONS_DIR = "video_captions"
VIDEO_COMMENTS_DIR = "video_comments"
PLAYLISTS_DIR = "playlists"

class Video(object):

    def _all_comments(self, thread, replies):
        """
        Yields all comments for a video (regardless if comment is top level comment or reply)
        """
        for post in thread:
            #yield top level comment
            yield (post["snippet"]["topLevelComment"], post["snippet"]["totalReplyCount"])
            #yield replies to top level comment
            if post["snippet"]["totalReplyCount"] <= 5:
                if "replies" in post:
                    for reply in post["replies"]["comments"]:
                        yield (reply, 0)
            else:
                for reply in replies[post["id"]]:
                    yield(reply, 0)

    def _parse_duration(self, duration_str):
        h = re.search(r"(\d+)H", duration_str)
        try:
            h = int(h.group(0)[:-1]) * 60 * 60
        except:
            h = 0
        m = re.search(r"(\d+)M", duration_str)
        try:
            m = int(m.group(0)[:-1]) * 60 
        except:
            m = 0            
        s = re.search(r"(\d+)S", duration_str)
        try:
            s = int(s.group(0)[:-1]) 
        except:
            s = 0
        #print(h+ m+ s)
        return h + m + s

    def __init__(self, channel_file, channel_zip, video_id):
        #video_meta = os.path.join(channel_dir, "video_meta")
        video_meta_filepath = os.path.join(VIDEO_METADATA_DIR, "{}.json".format(video_id))
        video_meta_data =  json.loads(channel_zip.read(video_meta_filepath).decode())

        meta = video_meta_data["items"][0]
        snippet = meta["snippet"]
        content_details = meta["contentDetails"]

        self.channel_file = channel_file

        #general video metadata
        self.id = video_id
        self.title = snippet["title"]
        self.description = snippet["description"]
        self.pub_date = snippet["publishedAt"]
        #self.channel_dir = channel_dir
        self.playlists = []
        self.duration = self._parse_duration(content_details["duration"])

        #get tags and categories
        self.tags = snippet["tags"] if "tags" in snippet else[]
        self.categories = [ x for x in meta["topicDetails"]["topicCategories"] ] if "topicDetails" in meta else []

        #get statistics
        if "statistics" in meta:
            self.views = int(meta["statistics"]["viewCount"]) if "viewCount" in meta["statistics"] else None
            self.likes = int(meta["statistics"]["likeCount"]) if "likeCount" in meta["statistics"] else None
            self.dislikes = int(meta["statistics"]["dislikeCount"]) if "dislikeCount" in meta["statistics"] else None
            self.favorites = int(meta["statistics"]["favoriteCount"]) if "favoriteCount" in meta["statistics"] else None
            self.comment_count = int(meta["statistics"]["commentCount"]) if "commentCount" in meta["statistics"] else None

        #load comments
        self.comment_users = []
        self.comments = []

        comments_filepath = os.path.join(VIDEO_COMMENTS_DIR, "{}_threads.json".format(self.id))
        replies_filepath = os.path.join(VIDEO_COMMENTS_DIR, "{}_comments.json".format(self.id))
        try:
            comments_data = json.loads(channel_zip.read(comments_filepath).decode())
        except:
            print("no comments available for <{}>".format(self.id))
            return
        try: 
            replies_data = json.loads(channel_zip.read(replies_filepath).decode())
        except:
            replies_data = {}

        for post, reply_count in self._all_comments(comments_data, replies_data):
            id_ = post["id"]
            author_name = post["snippet"]["authorDisplayName"]
            text = post["snippet"]["textOriginal"]
            timestamp = post["snippet"]["publishedAt"]
            likes = post["snippet"]["likeCount"]
            if reply_count > 0 or "." in id_:
                comment_thread = id_.split(".")[0].strip()
            else:
                comment_thread = None
            if "parentId" in post["snippet"]:
                parent_id = post["snippet"]["parentId"]
            else:
                parent_id = None

            if "authorChannelId" in post["snippet"]:
                author_id =  post["snippet"]["authorChannelId"]["value"]
            else:
                print("NO AUTHOR CHANNEL ID")
                author_id = None

            self.comments.append({
                "id": id_,
                "author": author_name,
                "author_id":author_id, 
                "text": text,
                "parent_id": parent_id,
                "reply_count": reply_count,
                "comment_thread": comment_thread,
                "timestamp": timestamp,
                "likes": likes
            })
        self.comment_users = [x["author"] for x in self.comments]

    def comment_stats(self):
        """
        Returns comment count per user, ordered by comment count
        """
        user_count = Counter(self.comment_users)
        user_count = list(sorted( dict(user_count).items(), key=lambda x: -x[1] ))
        return user_count

    def users(self):
        """
        Returns a distinct list of users writing  a comment
        """
        return list(set(self.comment_users))

    def caption(self, filetype="txt"):
        """
        Loads caption (if available) for video.
        """
        caption_filepath = os.path.join(VIDEO_CAPTIONS_DIR, "{}.{}".format(self.id, filetype))
        with zipfile.ZipFile(self.channel_file) as zf:
            try:
                caption = zf.read(caption_filepath)
                return caption.decode()
            except:
                return None

    def comments_by_user(self, user):
        for comment in self.comments:
            if user == comment["author"]:
                yield comment


class Playlist(object):

    def _load_video_ids(self, channel_zip):
        playlist_filepath = os.path.join(PLAYLISTS_DIR, "{}.json".format(self.id))
        playlist_data = json.loads(channel_zip.read(playlist_filepath).decode())
        self.video_ids = [ x["snippet"]["resourceId"]["videoId"] for x in playlist_data ]


    def __init__(self, id_, title, channel_zip):
        #self.playlist_dir = playlist_dir
        self.id = id_
        self.title = title
        self._load_video_ids(channel_zip)

    def contains_video(self, video_id):
        if video_id in self.video_ids:
            return True
        else:
            return False


class ChannelReader(object):
    """
    Reader class for scraped youtube channels
    """

    def _load_video_metadata(self):
        """
        Loads video metadata, captions and comments into the YoutubeChannel object
        """
        for video_id in tqdm(self.video_ids):
            #load video metadata form zip file
            self.videos.append(Video(self.channel_file, self.channel_zip, video_id))

    def _load_playlists(self):
        """
        loads all playlists from channel and updates videos with playlist information
        """
        playlists_list = json.loads(self.channel_zip.read("playlists.json"))
        for playlist in playlists_list:
            id_ = playlist["id"]
            title = playlist["snippet"]["title"]
            self.playlists.append(Playlist(id_, title, self.channel_zip))
        self._update_video_playlists()
      
    def _update_video_playlists(self):
        for video in self.videos:
            for playlist in self.playlists:
                if playlist.contains_video(video.id):
                    video.playlists.append({
                        "id": playlist.id,
                        "title": playlist.title
                    })


    def __init__(self, channel_name=None, filepath=None):
        """
        Initialize YoutubeChannel object with corpurs data directory and channel name
        """
        if channel_name:
            CF = load_config()
            self.channel_file = os.path.join(CF["PROJECT_DIR"],"channels", "{}.zip".format(channel_name))
        else:
            self.channel_file = filepath
        self.videos = []
        self.playlists = []
        
        self.channel_zip = zipfile.ZipFile(self.channel_file)

        self.video_ids = json.loads(self.channel_zip.read("video_ids.json").decode())
        self._load_video_metadata()
        self._load_playlists()
        
        self.channel_zip.close()


    def _videos(self):
        for video in self.videos:
            yield video

    ### video generators
    def videos_by_tag(self, tag):
        for video in self._videos():
            if tag in video.tags:
                yield video
    
    def videos_by_category(self, category):
        for video in self._videos():
            if category in video.categories:
                yield video

    def videos_by_user(self, user):
        for video in self._videos():
            if user in video.users():
                yield video
    #####

    #### comment generators
    def get_all_comments(self):
        comments = []
        for video in self._videos():
            comments += [ x["text"] for x in video.comments ]
        return comments

    def all_comments_by_user(self, user):
        all_comments = []
        for video in tqdm(self._videos()):
            all_comments += [ c for c in video.comments_by_user(user) ]
        return all_comments
    ######

    def get_all_captions(self):
        captions = []
        for video in tqdm(self._videos()):
            captions.append(video.caption())
        return captions


    #### video stats
    def user_stats(self):
        user_dict = defaultdict(int)
        for video in self._videos():
            for user in video.users():
                user_dict[user] += 1
        return sorted(user_dict.items(), key=lambda x: -x[1])

    def video_by_id(self, id_):
        for video in self.videos:
            if video.id == id_:
                return video            

