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
import zipfile

from tqdm import tqdm
from collections import Counter, defaultdict

from .config import load_config, VIDEO_CAPTIONS_DIR, VIDEO_COMMENTS_DIR, VIDEO_METADATA_DIR, PLAYLISTS_DIR
from .zip_archive import ZipArchive

class YoutubeArchiveReader(object):

    def __init__(self, filepath):
        self._archive = ZipArchive(filepath)
        self._update_files = self._get_update_files(filepath)

        self.video_ids = []
        self.videos = {}
        self.playlists = []

        for video_id, archive in self._all_video_ids():
            self.video_ids.append(video_id)
            video = Video(archive, video_id)
            self.videos[video.id] = video


        #pl = self._archive.get("playlists.json")
        #print(pl)

        if self._archive.contains("playlists.json"):
            #print("build playlist")
            self._load_playlists()


    def _all_video_ids(self):
        video_ids = { video_id: self._archive for video_id in self._archive.get("video_ids.json") }
        for update_file in self._update_files:
            for updated in update_file.get("video_ids.json"):
                video_ids[updated] = update_file
        
        for video_id, archive in video_ids.items():
            yield video_id, archive


    def _get_update_files(self, filepath):

        update_files = []

        base_path = os.path.dirname(filepath)
        archive = os.path.basename(filepath)
        for filename in sorted(os.listdir(base_path)):
            if archive != filename and filename.startswith(archive.replace(".zip", "")) and not filename.endswith(".prov"):
                print(filename)
                update_files.append(ZipArchive(os.path.join(base_path, filename)))
        return update_files


    def _load_video(self, video_id):
        return self.videos[video_id]

    def __iter__(self):
        for video in self.videos.values():
            yield video

    def _load_playlists(self):
        """
        loads all playlists from channel and updates videos with playlist information
        """
        playlist_list = self._archive.get("playlists.json")

        for playlist in playlist_list:
            id_ = playlist["id"]
            title = playlist["snippet"]["title"]
            self.playlists.append(Playlist(id_, title, self._archive))
        self._update_video_playlists()
      
    def _update_video_playlists(self):
        for video in self:
            for playlist in self.playlists:
                if video.id in playlist:
                    video.playlists.append({
                        "id": playlist.id,
                        "title": playlist.title
                    })

    def __getitem__(self, video_id):
        video = self._load_video(video_id)
        return video



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

    def __init__(self, archive, video_id):

        self._archive = archive

        video_meta_filepath = os.path.join(VIDEO_METADATA_DIR, "{}.json".format(video_id))
        video_meta_data =  archive.get(video_meta_filepath)

        meta = video_meta_data["items"][0]
        snippet = meta["snippet"]
        content_details = meta["contentDetails"]

        #general video metadata
        self.id = video_id
        self.title = snippet["title"]
        self.description = snippet["description"]
        self.pub_date = snippet["publishedAt"]
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

        if VIDEO_COMMENTS_DIR in self._archive:

            comments_filepath = os.path.join(VIDEO_COMMENTS_DIR, "{}_threads.json".format(self.id))
            replies_filepath = os.path.join(VIDEO_COMMENTS_DIR, "{}_comments.json".format(self.id))
            try:
                comments_data = archive.get(comments_filepath)
            except:
                print("no comments available for <{}>".format(self.id))
                return
            
            replies_data = archive.get(replies_filepath)
            
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
        if VIDEO_CAPTIONS_DIR in self._archive:
            caption_filepath = os.path.join(VIDEO_CAPTIONS_DIR, "{}.{}".format(self.id, filetype))
            return self._archive.get(caption_filepath)
        else:
            return None

    def comments_by_user(self, user):
        for comment in self.comments:
            if user == comment["author"]:
                yield comment


class Playlist(object):

    def _load_video_ids(self):
        playlist_filepath = os.path.join(PLAYLISTS_DIR, "{}.json".format(self.id))
        playlist_data = self._archive.get(playlist_filepath)
        # playlist_data = json.loads(channel_zip.read(playlist_filepath).decode())
        self.video_ids = [ x["snippet"]["resourceId"]["videoId"] for x in playlist_data ]


    def __init__(self, id_, title, archive):
        #self.playlist_dir = playlist_dir
        self._archive = archive
        self.id = id_
        self.title = title
        self._load_video_ids()

    def __contains__(self, video_id):
        if video_id in self.video_ids:
            return True
        else:
            return False
