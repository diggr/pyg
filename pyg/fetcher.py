#!/usr/bin/env python3
"""
Fetch classes for youtube channel and videos

Use:
from youtubetools.fetcher import ChannelFetcher, VideoFetcher

ChannelFetcher("channel_title")
VideoFetcher(["list", "of", "video", "ids"], project_name="project_name)

Output:
<pyg_project_dir>/channels/<channel_title_or_project_name>.zip
                           <channel_title_or_project_name>.zip.prov
"""

import re
import requests
import json
import os
import lxml
import html
import time
import zipfile

from datetime import datetime
from provit.prov import Provenance
from tqdm import tqdm
from bs4 import BeautifulSoup
from apiclient.discovery import build


from .zip_archive import ZipArchive
from .reader import YoutubeArchiveReader
from .utils import get_channel_id, remove_html
from .config import load_config, PROV_AGENT, DATA_DIR

YOUTUBE_URL = "https://www.youtube.com/watch?v={id}"

class YoutubeFetcher(object):
    """
    Fetcher base class:
    Contains function for initialising directories and fetching video data
    """

    # ARCHIVE DIRECTORIES
    CHANNELS = os.path.join(DATA_DIR, "channels")
    VIDEOS = os.path.join(DATA_DIR, "videos")

    VCAPTIONS = "video_captions"
    VMETA = "video_meta"
    VCOMMENTS = "video_comments"
    PLAYLISTS = "playlists"


    def __init__(self):
        """
        Initialize directories and set up youtube api
        """

        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
        if not os.path.exists(self.CHANNELS):
            os.makedirs(self.CHANNELS)
        if not os.path.exists(self.VIDEOS):
            os.makedirs(self.VIDEOS)

        CF = load_config()
        self.youtube =  build('youtube', 'v3', developerKey=CF["YOUTUBE_API_KEY"])


    def _init_archive(self, name, type_, group="main"):
        """
        Initialises zip archive file for youtube fetch project
        """
        if type_ == "channels":
            self._dir = os.path.join(self.CHANNELS, group)
        elif type_ == "videos":
            self._dir = self.VIDEOS

        if not os.path.exists(self._dir):
            os.mkdir(self._dir)

        self.filepath = os.path.join(self._dir, "{}.zip".format(name))
        if self._skip and os.path.exists(self.filepath):
            return True
        else:
            self._archive = ZipArchive(self.filepath)
            return False


    def _load_video_metadata(self, video_id):
        """
        Load video metadata from youtube api
        """

        while True:
            try:
                video_data = self.youtube.videos().list(
                    part="id,recordingDetails,snippet,statistics,status,topicDetails,contentDetails",
                    id=video_id
                    ).execute()       
                break
            except:
                print("retrying fetching video metadata ...")
                continue

        return video_data

    def _fetch_video_metadata(self, video_id):
        """
        Fetches metadata for a youtube video from the youtube api
        """

        #check if metadata already in archive
        metadata_filepath = os.path.join(self.VMETA, "{}.json".format(video_id))
        if metadata_filepath in self._archive:
            print(" ... Metadata for video '{}' already fetched".format(video_id))
            return

        video_data = self._load_video_metadata(video_id)
        self._archive.add(metadata_filepath, video_data)

    def _fetch_video_comments(self, video_id):
        """
        Fetches comments (top level comments + replies) for a youtube video 
        from the youtube api.
        """

        threads_filepath = os.path.join(self.VCOMMENTS, "{}_threads.json".format(video_id))
        thread_comments_filepath =  os.path.join(self.VCOMMENTS, "{}_comments.json".format(video_id))

        if threads_filepath in self._archive:
            print(" ... Comments for video '{}' already fetched".format(video_id))
            return

        #get all comment threads (top level comments + first five replies)
        threads= []
        next_page = None
        offset = 0
        while True:
            #print(offset)
            offset += 100
            #try:
            retries = 0
            while True:
                try:
                    comment_threads = self.youtube.commentThreads().list(
                        part="snippet,replies",
                        videoId=video_id,
                        maxResults=100,
                        pageToken=next_page
                    ).execute()
                    break
                except: 
                    retries += 1
                    print("retrying fetching comment data ...")

                    if retries > 15:
                         print("\t fetching comment threads for video <{}> failed".format(video_id))
                         break

                    continue
            # except:
            #     print("\t fetching comment threads for video <{}> failed".format(video_id))
            #     print(offset)
            #     break
            if retries > 15:
                break

            threads += comment_threads["items"]
            if "nextPageToken" in comment_threads:
                next_page = comment_threads["nextPageToken"]
            else:
                break

        if len(threads) > 0:
            self._archive.add(threads_filepath, threads)

            #get all replies for threads with more than 5 replies
            thread_comments = {}
            for thread in threads:
                if thread["snippet"]["totalReplyCount"] > 5:
                    thread_all_comments = []
                    next_page = None
                    while True:

                        while True:
                            try:
                                comments = self.youtube.comments().list(
                                    part='snippet',
                                    parentId=thread["id"],
                                    maxResults=100,
                                    pageToken=next_page
                                ).execute()
                                break
                            except:
                                print("retrying fetchen comment data ...")
                                continue
                        
                        thread_all_comments += comments["items"]
                        if "nextPageToken" in comments:
                            next_page = comments["nextPageToken"]
                        else:
                            break    
                    thread_comments[thread["id"]] = thread_all_comments

            self._archive.add(thread_comments_filepath, thread_comments)

    def _get_caption_url(self, source):
        """
        Extracts youtube caption xml url from html source
        """
        m = re.search(r'captionTracks(.+?)name', source)
        if m:
            base = m.group(1)
            baseurl = base.split("https")[-1][5:]
            callurl = baseurl.replace("\\/", "/").replace("\\\\u0026", "&").split("\\")[0]
            return "http://"+callurl
        else:
            return None

    def _get_caption_xml(self, video_id):
        """
        Retrieves youtube cation xml file for video id
        """
        rsp = requests.get(YOUTUBE_URL.format(id=video_id))

        caption_url = self._get_caption_url(rsp.text)
        if caption_url:
            rsp = requests.get(caption_url)
            return rsp.text
        else:
            return None

    def _caption_xml_to_str(self, xml):
        """
        Converts youtube caption xml into plain text
        """
        soup = BeautifulSoup(xml, "lxml")
        lines = []
        for line in soup.find_all("text"):
            lines.append(remove_html(line.text))
        return html.unescape(" ".join(lines))


    def _fetch_video_captions(self, video_id):
        """
        Fetches youtube captions for each video in channel
        """
        xml_filepath = os.path.join(self.VCAPTIONS, "{}.xml".format(video_id))
        txt_filepath = os.path.join(self.VCAPTIONS, "{}.txt".format(video_id))

        if xml_filepath in self._archive:
            print(" ... Captions for video '{}' already fetched".format(video_id))
            return
            

        captions_xml = self._get_caption_xml(video_id)

        if captions_xml:
            captions_txt = self._caption_xml_to_str(captions_xml)
            
            self._archive.add(xml_filepath, captions_xml)
            self._archive.add(txt_filepath, captions_txt)

            time.sleep(0.5)


class VideoFetcher(YoutubeFetcher):
    """
    Youtube video fetcher class.
    Initializes with a list of video ids.
    Fetches video data and saves them into a zip archive.
    """

    def __init__(self, video_ids, project_name="video_collection", comments=True, captions=True, skip=True):
        super().__init__()

        self._skip = skip

        self._init_archive(project_name, type_="videos")

        self._archive.add("video_ids.json", video_ids)

        
        for i, video_id in enumerate(video_ids):
            print ("{}/{}".format(i, len(video_ids)))
            self._fetch_video_metadata(video_id)
            if comments:
                self._fetch_video_comments(video_id)
            if captions:
                self._fetch_video_captions(video_id)

        self._archive.add_provenance (
            agents=[ PROV_AGENT ], 
            activity="fetch_video_collection", 
            description="Youtube video/comment data for collection <{}>".format(project_name))


class ChannelFetcher(YoutubeFetcher):
    """
    Youtube channel fatcher class.
    Initialize with channel id.
    Fetch channel related data by calling the corresponding methods.
    """

    def __init__(self, channel, captions=True, comments=True, skip=True, group="main"):
        #self.youtube =  build('youtube', 'v3', developerKey="AIzaSyCGhgLFUtvUyYRKnM913vFRY3paBLCqW4c")

        super().__init__()

        self._captions = captions
        self._comments = comments
        self._skip = skip

        
        print(channel)
        #get channel id
        if "channel/" in channel:
            channel_id = channel.replace("channel/", "").strip()
        elif "user/" in channel:
            channel_id = get_channel_id(self.youtube, channel.replace("user/", "").strip())
        self.channel_id = channel_id


        #fetch channel meta data
        self.channel_metadata = self.youtube.channels().list(
            part="contentDetails,snippet,brandingSettings,contentOwnerDetails,invideoPromotion,statistics,status,topicDetails",
            id=channel_id
            ).execute()

        if not self.channel_metadata["items"]:
            print("\t Invalid channel ID")
        else:

            self.channel_title = self.channel_metadata["items"][0]["snippet"]["title"]
            skip = self._init_archive(self.channel_title, type_="channels", group=group)

            if not skip:
                self._fetch_channel_comments()
                self._fetch_playlists()
                self._fetch_channel()

                self._archive.add_provenance(
                    agents=[ PROV_AGENT ], 
                    activity="fetch_channel", 
                    description="Youtube video/comment data for channel <{}>".format(self.channel_title))


    def _fetch_channel(self):
        """
        Fetches video data of a youtube channel
        """
        #save channel meta data
        channel_meta_filepath = "channel_meta.json"
        if channel_meta_filepath not in self._archive:        
            self._archive.add(channel_meta_filepath, self.channel_metadata)

        print("fetching video data ...")

        videos_filepath = "video_ids.json"
        if videos_filepath in self._archive:
            video_ids = self._archive.get(videos_filepath)
        else:   
            # get id of uploads playlist
            uploads = self.channel_metadata["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

            # get all video ids in uploads playlist
            video_ids = []
            next_page = None
            while True:
                playlist_page = self.youtube.playlistItems().list(
                    playlistId=uploads,
                    part="snippet,status",
                    maxResults=50,
                    pageToken=next_page
                ).execute()
                video_ids += [ x["snippet"]["resourceId"]["videoId"] for x in playlist_page["items"] ]
                
                if "nextPageToken" in playlist_page:
                    next_page = playlist_page["nextPageToken"]
                else:
                    break
            self._archive.add(videos_filepath, video_ids)

        for i, video_id in enumerate(video_ids):  
            print("{}/{}".format(i, len(video_ids)))
            self._fetch_video_metadata(video_id)
            if self._comments:
                self._fetch_video_comments(video_id)
            if self._captions:
                self._fetch_video_captions(video_id)                

    def _fetch_playlists(self):
        """
        Fetch playlist data for a youtube channel from the api
        """

        print("fetching playlists meta data ...")

        #get list of  playlists
        playlists = []
        next_page = None

        #save playlists file
        playlists_filepath = "playlists.json"
        if playlists_filepath not in self._archive:

            while True:
                playlist_page = self.youtube.playlists().list(part="snippet", channelId=self.channel_id, maxResults=50, pageToken=next_page).execute()
                playlists += playlist_page["items"]
                if "nextPageToken" in playlist_page:
                    next_page = playlist_page["nextPageToken"]
                else:
                    break

            self._archive.add(playlists_filepath, playlists)
        else:
            playlists = self._archive.get(playlists_filepath)

        #get meta data for each playlists
        for playlist in playlists:

            playlist_id = playlist["id"]
            playlist_filepath = os.path.join(self.PLAYLISTS, "{}.json".format(playlist_id))
            if playlist_filepath in self._archive:
                continue

            #get all playlist items for each playlist
            playlist_items = []
            next_page = None
            while True:
                playlist_page = self.youtube.playlistItems().list(
                    playlistId=playlist_id,
                    part="snippet,status",
                    maxResults=50,
                    pageToken=next_page
                ).execute()
                playlist_items += playlist_page["items"]
                if "nextPageToken" in playlist_page:
                    next_page = playlist_page["nextPageToken"]
                else:
                    break

            self._archive.add(playlist_filepath, playlist_items)

    def _fetch_channel_comments(self):
        """
        Fetches comment threads for the youtube channel
        """
        print("fetching channel comments ...")

        channel_comments_filepath = "channel_comments.json"
        if channel_comments_filepath in self._archive:
            return

        all_comments = []
        next_page = None
        while True:
            try:
                comment_threads = self.youtube.commentThreads().list(
                    part="snippet,replies",
                    channelId=self.channel_id,
                    maxResults=100,
                    pageToken=next_page
                ).execute()
            except:
                print("\t API call failed")
                return

            all_comments += comment_threads["items"]
            if "nextPageToken" in comment_threads:
                next_page = comment_threads["nextPageToken"]
            else:
                break
        self._archive.add(channel_comments_filepath, all_comments)


class ChannelUpdateFetcher(YoutubeFetcher):
    """
    Generates a diff file for each channel, containing new videos and videos where the comment count changed
    """

    def __init__(self, channel, archive_filepath):
        super().__init__()


        archive = ZipArchive(archive_filepath)
        self.channel_metadata = archive.get("channel_meta.json")
        channel_id = self.channel_metadata["items"][0]["id"]
        self.channel_title = self.channel_metadata["items"][0]["snippet"]["title"]

        self._current = YoutubeArchiveReader(archive_filepath)


        diff_filepath = os.path.join(os.path.dirname(archive_filepath), "{}_{}.zip".format(self.channel_title, datetime.now().isoformat()[:19]))
        self._archive = ZipArchive(diff_filepath)

        updated = []
        print("Update youtube channel <{}>".format(self.channel_title))

        uploads = self.channel_metadata["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        # get all video ids in uploads playlist
        video_ids = []
        next_page = None
        while True:
            playlist_page = self.youtube.playlistItems().list(
                playlistId=uploads,
                part="snippet,status",
                maxResults=50,
                pageToken=next_page
            ).execute()
            video_ids += [ x["snippet"]["resourceId"]["videoId"] for x in playlist_page["items"] ]
            
            if "nextPageToken" in playlist_page:
                next_page = playlist_page["nextPageToken"]
            else:
                break            

        for i, video_id in enumerate(video_ids):
            print("{}/{}".format(i, len(video_ids)))
            if video_id  in self._current.video_ids:
                video = self._current[video_id]
                comment_count = video.comment_count

                new_meta = self._load_video_metadata(video_id)
                meta = new_meta["items"][0]
                new_comment_count = int(meta["statistics"]["commentCount"]) if "commentCount" in meta["statistics"] else None

                if comment_count == new_comment_count:
                    continue

            updated.append(video_id)
            self._fetch_video_metadata(video_id)
            self._fetch_video_comments(video_id)
            self._fetch_video_captions(video_id)

        if len(updated) == 0:
            os.remove(diff_filepath)
        else:
            self._archive.add("video_ids.json", updated)
            self._archive.add_provenance(
                agents=[ PROV_AGENT ], 
                activity="update_channel", 
                description="Youtube video/comment update data for channel <{}>".format(self.channel_title))

