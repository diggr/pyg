#!/usr/bin/env python3
"""
Fetch class for youtube channel

Use:
from youtubetools.fetcher import YoutubeChannelFetcher

fetcher = YoutubeChannelFetcher(channel="<channel_id>")
fetcher.get_channel_comments()
fetcher.get_video_metadata()
fetcher.get_video_comments()
fetcher.get_video_captions()
fetcher.archive_channel()

Output:
<pyg_project_dir>/channels/<channel_title>.zip
                           <channel_title>.zip.prov
"""

import requests
import json
import os
import re
import requests
import lxml
import html
import time
import pickle
import zipfile
import shutil

from tqdm import tqdm
from bs4 import BeautifulSoup
from apiclient.discovery import build

from .utils import get_channel_id
from .config import load_config, PROV_AGENT
from .pit import Provenance

YOUTUBE_URL = "https://www.youtube.com/watch?v={id}"

TMP_DIR = "tmp"
OUT_DIR = "channels"

class ChannelFetcher(object):
    """
    Youtube channel fatcher class.
    Initialize with channel id.
    Fetch channel related data by calling the corresponding methods.
    """

    DATA = "data"
    BASE = "base"
    VCAPTIONS = "video_captions"
    VMETA = "video_meta"
    VCOMMENTS = "video_comments"
    PLAYLISTS = "playlists"

    def dirs_it(self, base_name, dirs=[VCAPTIONS, VMETA, VCOMMENTS, PLAYLISTS,]):
        """
        Generator iterating over all output directories.
        data_dir:
        """
        yield self.DATA, self.data_dir
        yield self.BASE, os.path.join(self.data_dir, base_name)
        for dir_name in dirs:
            yield dir_name, os.path.join(self.data_dir, base_name, dir_name)

    def _init_data_dirs(self):
        """
        Initializes directories where scraped/fetched content will be saved to.
        """
        self.data_sub_dirs = dict()
        for sub_dir_name, sub_dir in self.dirs_it(self.channel_title):
            if not os.path.exists(sub_dir):
                os.makedirs(sub_dir)
            self.data_sub_dirs[sub_dir_name] = sub_dir

    def _save_requests_session(self):
        """
        Pickles the current requests Session object to be reused in the next run of the tool.
        """
        with open(self.pickle_file, 'wb') as outfile:
            pickle.dump(self.rs, outfile)

    def __init__(self, channel):
        """
        Initialize youtube channel fetcher with channel id,
                                                data directory,
                                                and google api key.
        Fetches channel metadata and ids of all videos
        """

        CF = load_config()

        self.youtube =  build('youtube', 'v3', developerKey=CF["YOUTUBE_API_KEY"])

        #get channel id
        if "channel/" in channel:
            channel_id = channel.replace("channel/", "").strip()
        elif "user/" in channel:
            channel_id = get_channel_id(self.youtube, channel.replace("user/", "").strip())
        self.channel_id = channel_id

        #init temp and export direcotry
        self.data_dir = os.path.join(CF["PROJECT_DIR"], TMP_DIR)
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        self.export_dir= os.path.join(CF["PROJECT_DIR"], OUT_DIR)
        if not os.path.exists(self.export_dir):
            os.makedirs(self.export_dir)     
        

        #fetch channel meta data
        self.channels = self.youtube.channels().list(
            part="contentDetails,snippet,brandingSettings,contentOwnerDetails,invideoPromotion,statistics,status,topicDetails",
            id=channel_id
            ).execute()

        if not self.channels["items"]:
            print("\t Invalid channel ID")
        else:
            self.fetch_channel()

            #self._save_requests_session()

    def archive_channel(self):
        """
        Archives youtube channel into compressed zip file and removes temp channel dir
        """
        target_filepath = os.path.join(self.export_dir, "{}.zip".format(self.channel_title))
        print("\t building archive for channel <{}>".format(self.channel_title))
        with zipfile.ZipFile(target_filepath, "w", zipfile.ZIP_DEFLATED) as zf:
            for filepath, dirs, files in os.walk(self.channel_dir):
                print("\t\t compress {}".format(filepath))
                for file_name in files:
                    source_filepath = os.path.join(filepath, file_name)
                    zf.write(source_filepath, os.path.relpath(source_filepath, self.channel_dir))
        
        #add provenance information
        prov = Provenance(target_filepath)
        prov.add(
            agent=PROV_AGENT, 
            activity="fetch_yt_channel", 
            description="Full youtube channel <{}>: Metadata, comments and captions".format(self.channel_title))
        prov.add_primary_source("youtube", url="https://www.youtube.com")
        prov.save()

        shutil.rmtree(self.data_dir)




    def fetch_channel(self):
        self.channel_title = self.channels["items"][0]["snippet"]["title"]
        self._init_data_dirs()
        self.channel_dir = self.data_sub_dirs[self.BASE]

        if os.path.exists(os.path.join(self.channel_dir, "video_ids.json")):
            print("Channel already downloaded")
        else:

            # Initialize requests session
            self.pickle_file = os.path.join(self.channel_dir, "{}.pkl".format(self.channel_title))
            try:
                self.rs = pickle.load(open(self.pickle_file, 'rb'))
                print("Loaded pickled session.")
            except FileNotFoundError:
                self.rs = requests.Session()


            print("initialising channel {} ...".format(self.channel_title))

            # get id of uploads playlist
            uploads = self.channels["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

            # get all video ids in uploads playlist
            playlist_items = []
            next_page = None
            while True:
                playlist_page = self.youtube.playlistItems().list(
                    playlistId=uploads,
                    part="snippet,status",
                    maxResults=50,
                    pageToken=next_page
                ).execute()
                playlist_items += [ x["snippet"]["resourceId"]["videoId"] for x in playlist_page["items"] ]
                
                if "nextPageToken" in playlist_page:
                    next_page = playlist_page["nextPageToken"]
                else:
                    break

            #save channel meta data
            channel_meta = os.path.join(self.channel_dir, "channel_meta.json")
            with open(channel_meta, "w") as f:
                json.dump(self.channels, f, indent=4)

            #save video ids
            uploads_filepath = os.path.join(self.channel_dir, "video_ids.json")
            with open(uploads_filepath, "w") as f:
                json.dump(playlist_items,f, indent=4)
            self.video_ids = playlist_items

            print("\t Number of videos: {}".format(len(self.video_ids)))


    def get_video_metadata(self):
        """
        Get video meta data for each video id in channel
        """
        print("fetching video metadata ...")
        for video_id in tqdm(self.video_ids):
            video_data = self.youtube.videos().list(
                part="id,recordingDetails,snippet,statistics,status,topicDetails,contentDetails",
                id=video_id
                ).execute()

            data_filepath = os.path.join(self.data_sub_dirs[self.VMETA], "{}.json".format(video_id))
            with open(data_filepath, "w") as f:
                json.dump(video_data, f, indent=4)


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
        rsp = self.rs.get(YOUTUBE_URL.format(id=video_id))

        caption_url = self._get_caption_url(rsp.text)
        if caption_url:
            rsp = self.rs.get(caption_url)
            return rsp.text
        else:
            return None


    def _remove_html(self,text):
        """
        Removes html tags from text
        """
        return re.sub('<[^<]+?>', '', text)


    def _caption_xml_to_str(self, xml):
        """
        Converts youtube caption xml into plain text
        """
        soup = BeautifulSoup(xml, "lxml")
        lines = []
        for line in soup.find_all("text"):
            lines.append(self._remove_html(line.text))
        return html.unescape(" ".join(lines))


    def get_video_captions(self):
        """
        Fetches youtube captions for each video in channel
        """
        print("fetching video captions ...")
        for video_id in tqdm(self.video_ids):

            caption_xml = self._get_caption_xml(video_id)
            if caption_xml:
                caption_txt = self._caption_xml_to_str(caption_xml)

                #save caption files
                xml_filepath = os.path.join(self.data_sub_dirs[self.VCAPTIONS], "{}.xml".format(video_id))
                txt_filepath = os.path.join(self.data_sub_dirs[self.VCAPTIONS], "{}.txt".format(video_id))
                with open(xml_filepath, "w", encoding="utf-8") as f:
                    f.write(caption_xml)
                with open(txt_filepath, "w", encoding="utf-8") as f:
                    f.write(caption_txt)

                time.sleep(0.5)


    def get_channel_comments(self):
        """
        Fetches comment threads for the youtube channel
        """
        print("fetching channel comments ...")
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

        filepath = os.path.join(self.channel_dir, "channel_comments.json")
        with open(filepath, "w") as f:
            json.dump(all_comments, f, indent=4)


    def get_video_comments(self):
        """
        Fetches comment threads for each video in channel
        """
        print("fetching video comment threads ...")
        for video_id in tqdm(self.video_ids):

            #get all comment threads (top level comments + first five replies)
            all_comments = []
            next_page = None
            filepath = os.path.join(self.data_sub_dirs[self.VCOMMENTS], "{}_threads.json".format(video_id))
            comment_filepath =  os.path.join(self.data_sub_dirs[self.VCOMMENTS], "{}_comments.json".format(video_id))

            if os.path.exists(filepath):
                with open(filepath) as f:
                    all_comments = json.load(f)
            else:
                while True:
                    try:
                        comment_threads = self.youtube.commentThreads().list(
                            part="snippet,replies",
                            videoId=video_id,
                            maxResults=100,
                            pageToken=next_page
                        ).execute()
                    except:
                        print("\t fetching comment threads for video <{}> failed".format(video_id))
                        break

                    all_comments += comment_threads["items"]
                    if "nextPageToken" in comment_threads:
                        next_page = comment_threads["nextPageToken"]
                    else:
                        break

                if len(all_comments) > 0:
                    with open(filepath, "w") as f:
                        json.dump(all_comments, f, indent=4)
        
            #get all replies for threads with more than 5 replies
            if not os.path.exists(comment_filepath):
                threads = {}
                for thread in all_comments:
                    if thread["snippet"]["totalReplyCount"] > 5:
                        thread_all_comments = []
                        next_page = None
                        while True:
                            comments = self.youtube.comments().list(
                                part='snippet',
                                parentId=thread["id"],
                                maxResults=100,
                                pageToken=next_page
                            ).execute()
                            thread_all_comments += comments["items"]
                            if "nextPageToken" in comments:
                                next_page = comments["nextPageToken"]
                            else:
                                break    
                        threads[thread["id"]] = thread_all_comments

                with open(comment_filepath, "w") as f:
                    json.dump(threads, f, indent=4)



    def get_playlists(self):
        print("fetching playlists meta data ...")

        #get list of  playlists
        playlists = []
        next_page = None
        while True:
            playlist_page = self.youtube.playlists().list(part="snippet", channelId=self.channel_id, maxResults=50, pageToken=next_page).execute()
            playlists += playlist_page["items"]
            if "nextPageToken" in playlist_page:
                next_page = playlist_page["nextPageToken"]
            else:
                break

        #save playlists file
        filepath = os.path.join(self.channel_dir, "playlists.json")
        with open(filepath, "w") as f:
            json.dump(playlists, f, indent=4)

        #get meta data for each playlists
        for playlist in tqdm(playlists):
            playlist_id = playlist["id"]

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

            filepath = os.path.join(self.data_sub_dirs[self.PLAYLISTS], "{}.json".format(playlist_id))
            with open(filepath, "w") as f:
                json.dump(playlist_items, f, indent=4)

#yongyea UCdoGgnZ4A3Pe3ogaJe1EtzQ
#vaatividya UCe0DNp0mKMqrYVaTundyr9w

if __name__ == "__main__":
    ycf = ChannelFetcher("UCe0DNp0mKMqrYVaTundyr9w")
