"""
Builds a youtube video network based on youtube's 'up next' recommendations.
Starting piont is a search term. The term will be looked up on youtube's search API,
and the top 30 videos will act as seed points for the network.
Per default the network goes two iterations deep. Increasing that number also increases
the size of the network exponentially. 

Use:

vrn = VideoRecommendationNetwork(q="searchterm", depth=2)

#save as graphml file
vrn.to_graphml()

"""

import json
import requests
import os
import networkx as nx
from tqdm import tqdm
from collections import defaultdict
from apiclient.discovery import build
from bs4 import BeautifulSoup

from .config import load_config, PROV_AGENT
from .pit import Provenance

OUT_DIR = "video_networks"

YOUTUBE_VIDEO = "https://www.youtube.com/watch?v={id}"

class VideoRecommendationNetwork(object):

    def _extract_video_ids(self, video_id):
        """
        extracts ids from recommended video list on a videos youtube page
        """
        resp = requests.get(YOUTUBE_VIDEO.format(id=video_id))
        soup = BeautifulSoup(resp.text, "html.parser")
        video_ids = set()

        for li in soup.find_all("li", {"class":"related-list-item"}):
            link = li.find("a")["href"]
            video_id = link.split("=")[-1].split("&")[0]
            video_ids.add(video_id)
        return list(video_ids)


    def _get_recommended_videos(self, video_id, depth):
        """
        fetches all recommended video_ids for a video_id recursivly (:deph: = number of iterations )
        """
        if depth > 0:
            self.videos.add(video_id)
            if video_id not in self.edgelist:
                recommended_videos = self._extract_video_ids(video_id)
            else:
                recommended_videos = self.edgelist[video_id]
            self.edgelist[video_id] = recommended_videos
            for recommended_video in recommended_videos:
                self.videos.add(recommended_video)
                self._get_recommended_videos(recommended_video, depth-1)

    def _get_value_or_0(self, item, elem):
        try:
            return int(item["statistics"][elem])
        except:
            return 0

    def _get_metadata(self):
        """
        gets video metada from youtube api for all videos in video network
        """
        for video_id in tqdm(self.videos):
            meta = self.youtube.videos().list(
                part="snippet,statistics",
                id=video_id
            ).execute()
            if len(meta["items"]) > 0: 
                item = meta["items"][0]
                #print(item)

                self.metadata[video_id] = {
                    "title": item["snippet"]["title"],
                    "channel": item["snippet"]["channelTitle"],
                    "views": self._get_value_or_0(item, "viewCount"),
                    "likes": self._get_value_or_0(item, "likeCount"),
                    "dislikes": self._get_value_or_0(item, "dislikeCount"),
                    "comments": self._get_value_or_0(item, "CommentCount")
                }
            else:
                print(video_id)

    def to_graphml(self, filepath= None):
        """
        saves video network as graphml file
        """        
        if not filepath:
            if self.name:
                filepath = os.path.join(self.out_dir, "{}.graphml".format(self.name))
            else:
                filepath = os.path.join(self.out_dir, "{}.graphml".format(self.seeds[0]))

        G = nx.DiGraph()

        for source, targets in self.edgelist.items():
            for target in targets:

                if source in self.metadata and target in self.metadata:
                    G.add_edge(source, target)
                
        for node in G.nodes:
            G.nodes[node]["label"] = self.metadata[node]["title"]
            G.nodes[node]["channel"] = self.metadata[node]["channel"]
            G.nodes[node]["views"] = self.metadata[node]["views"]
            G.nodes[node]["likes"] = self.metadata[node]["likes"]
            G.nodes[node]["dislikes"] = self.metadata[node]["dislikes"]
            G.nodes[node]["comments"] = self.metadata[node]["comments"]

        nx.write_graphml(G, filepath)

        #add provenance information
        prov = Provenance(filepath)
        if self.q:
            description = "Youtube recommended video network for q='{}' and depth <{}>".format(self.q, self.depth)
        else:
            description = "Youtube recommended video network for seeds='{}' and depth <{}>".format(self.seeds, self.depth)
        prov.add(
            agent=PROV_AGENT, 
            activity="video_network", 
            description=description)
        prov.add_primary_source("youtube", url="https://www.youtube.com")
        prov.save()

    def __init__(self, name=None, q=None, seeds=None, depth=2):

        CF = load_config()

        self.youtube =  build('youtube', 'v3', developerKey=CF["YOUTUBE_API_KEY"])

        self.name = name
        self.depth = depth

        self.out_dir = os.path.join(CF["PROJECT_DIR"], OUT_DIR)
        if not os.path.exists(self.out_dir):
            os.makedirs(self.out_dir)

        if q:
            self.q = q
            results = self.youtube.search().list(
                part="id,snippet",
                q=self.q,
                maxResults=30
            ).execute()
            self.seeds = [ x["id"]["videoId"] for x in results["items"] if "videoId" in x["id"] ]
        elif seeds:
            self.seeds = seeds

        self.videos = set()
        self.edgelist = defaultdict()
        self.metadata = defaultdict(dict)

        print("fetching related video data and building edgelist")
        for seed in tqdm(self.seeds):
            self._get_recommended_videos(seed, depth)

        print("get video metadata")
        self._get_metadata()
        #print(self.seeds)


if __name__ == "__main__":
    vrn = VideoRecommendationNetwork(q="Dark Souls lore", depth=2)
    vrn.to_graphml()



