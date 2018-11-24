"""
ChannelNetwork class for building a network of youtube channels based on the displayed related channels list

Usage:

#fetch channel network data and build edgelist
cn = ChannelList(channel_id=<str>, user_name=<str>, depth=<n>, featured=<bool>, data_dir=<str> )

#build and save graphml file of network
cn.to_graphml()

channel_id: id of channel to act as a starting point for the network
user_id: use when channel_id is not known; looks up username in the yt api
depth: depth of the network, number of iterations
featured: if True, use also featured channels list (otherwhise only related channels list is used)
data_dir: output directory

"""

import requests
import json
import time
import pickle
import os
import networkx as nx

from datetime import datetime
from bs4 import BeautifulSoup
from tqdm import tqdm
from collections import defaultdict
from apiclient.discovery import build

from pit.prov import Provenance

from .utils import get_channel_id
from .config import load_config, PROV_AGENT

OUT_DIR = "channel_networks"

YOUTUBE_CHANNEL = "https://www.youtube.com/channel/{id}"

class RelatedChannelsNetwork(object):
    """
    ChannelNetwork class builds a network of youtube channels based on a channels related and featured channels
    """

    def is_channel_available(self, soup):
        alerts = soup.find_all("div", {"class": "yt-alert-content"})
        if len(alerts) == 2:
            return False
        return True    

    def _extract_related_channels(self, soup):
        """
        Extracts and yield channel ids from related channels,
        skips popular channel list
        """
        popular_channels_header = [ "Beliebte Kanäle" ]
        related_channels_header = [ "Ähnliche Kanäle"]
        
        for related_channels_div in soup.find_all("div", {"class": "branded-page-related-channels"}):

            header = related_channels_div.find("h2").text.strip()
            #skip popular channel list
            if header in popular_channels_header:
                continue
            #if featured=False, skip featurec channel list
            if not self.featured and header not in related_channels_header:
                continue 
            for related_channel  in related_channels_div("li"):
                channel_link = related_channel.find("a")
                slug = channel_link["href"]
                if "user" in slug:
                    channel_id = get_channel_id(self.youtube, slug.replace("/user/","").strip())
                else:
                    channel_id = slug.replace("/channel/", "").strip()        
                yield channel_id            

    def _fetch_related_channels(self, channel_id):
        """
        fetches related channel list form youtube channel page
        """
        print("\tfetching related channels for <{}>".format(channel_id))
        related_channel_list = set()
        res = requests.get(YOUTUBE_CHANNEL.format(id=channel_id))
        soup = BeautifulSoup(res.text, "html.parser")
        if self.is_channel_available(soup):
            for channel_id in self._extract_related_channels(soup):
                related_channel_list.add(channel_id)

        return [ x for x in related_channel_list if x ]

    def _get_related_channels(self, seed, depth):
        """
        fetches all related channel from channel website
        """
        if depth > 0:
            self.channel_list.add(seed)
            
            related_channel_list = []
            if seed not in list(self.channel_relations.keys()):
                related_channel_list = self._fetch_related_channels(seed)
            else:
                related_channel_list = self.channel_relations[seed]

            self.channel_relations[seed] = related_channel_list
            self.channel_edgelist[seed] = related_channel_list

            for channel_id in list(set(related_channel_list)):
                self._get_related_channels(channel_id, depth-1)
                self.channel_list.add(channel_id)           

    def _get_metadata(self):
        """
        gets metadata for all the channels in the related channel network
        """
        for channel_id in tqdm(self.channel_list):
            if channel_id not in list(self.channel_metadata.keys()):
                meta = self.youtube.channels().list(
                    part="contentDetails,snippet,brandingSettings,contentOwnerDetails,invideoPromotion,statistics,status,topicDetails",
                    id=channel_id
                ).execute()
                try:
                    item = meta["items"][0]
                    self.channel_metadata[channel_id] = {
                        "id": item["id"],
                        "title": item["snippet"]["title"],
                        "subscribers": int(item["statistics"]["subscriberCount"]),
                        "videos": int(item["statistics"]["videoCount"]),
                        "views": int(item["statistics"]["viewCount"])
                    }
                except:
                    print(channel_id)

    def to_graphml(self):
        """
        Creates graphml file from related channel network, including channel stats for nodes
        """
        if self.name:
            filename = "{}_{}".format(self.name, datetime.now().isoformat()[:19].replace(":","_"))
            filepath = os.path.join(self.out_dir, "{}.graphml".format(filename))
        else: 
            seed_title = self.channel_metadata[self.seeds[0]]["title"]
            if self.featured:
                seed_title = "{}_f".format(seed_title)
            filename = "{}_{}".format(seed_title, datetime.now().isoformat())
            filepath = os.path.join(self.out_dir, "{}.graphml".format(seed_title))

        G = nx.DiGraph()
        #build edges
        for source, targets in self.channel_edgelist.items():
            for target in targets:
                if source in self.channel_metadata and target in self.channel_metadata:
                    G.add_edge(source, target)
        #add node properties
        for node in G.nodes:
            G.nodes[node]["views"] = self.channel_metadata[node]["views"]
            G.nodes[node]["subscribers"] = self.channel_metadata[node]["subscribers"]
            G.nodes[node]["videos"] = self.channel_metadata[node]["videos"]
            G.nodes[node]["label"] = self.channel_metadata[node]["title"]

        nx.write_graphml(G, filepath)
        prov = Provenance(filepath)
        prov.add(
            agent=PROV_AGENT, 
            activity="channel_network", 
            description="Youtube channel network for the seed channels <{}> and depth <{}>".format(self.seeds, self.depth))
        prov.add_primary_source("youtube", url="https://www.youtube.com")
        prov.save()

    def _load_cache(self):
        """
        loads channel data (relations and metadata) for caching 
        """
        #set up file path for cache files
        if self.featured:
            self.channel_relations_cache = os.path.join(self.out_dir, "channel_relations_f.yt")
            self.channel_metadata_cache = os.path.join(self.out_dir, "channel_metadata_f.yt")
        else:
            self.channel_relations_cache = os.path.join(self.out_dir, "channel_relations.yt")
            self.channel_metadata_cache = os.path.join(self.out_dir, "channel_metadata.yt")

        if os.path.exists(self.channel_relations_cache):
            with open(self.channel_relations_cache, "rb") as f:
                self.channel_relations = pickle.load(f)
        else:
            self.channel_relations = defaultdict(list) 

        if os.path.exists(self.channel_metadata_cache):
            with open(self.channel_metadata_cache, "rb") as f:
                self.channel_metadata = pickle.load(f)
        else:
            self.channel_metadata = defaultdict(list)         

    def _save_cache(self):
        """
        saves channel data (relations and metadata) for caching 
        """
        with open(self.channel_relations_cache, "wb") as f:
            pickle.dump(self.channel_relations, f)
        with open(self.channel_metadata_cache, "wb") as f:
            pickle.dump(self.channel_metadata, f)

    def __init__(self, name, seeds,  depth=5, featured=False):

        CF = load_config()

        self.youtube =  build('youtube', 'v3', developerKey=CF["YOUTUBE_API_KEY"])

        self.out_dir = os.path.join(CF["PROJECT_DIR"], OUT_DIR)
        if not os.path.exists(self.out_dir):
            os.makedirs(self.out_dir)

        seed_set = set()
        for seed in seeds:
            if "user/" in seed:
                seed_set.add(get_channel_id(self.youtube, seed.replace("user/", "").strip()))
            elif "channel/" in seed:
                seed_set.add(seed.replace("channel/", "").strip())
        self.seeds = list(seed_set)
        self.depth = depth

        self.featured = featured
        self.name = name

        self._load_cache()
        self.channel_edgelist = defaultdict(list)
        self.channel_list = set()
        
        print("fetching related channels")
        for seed in self.seeds:
            self._get_related_channels(seed, depth)
        print("getting channel metadata")
        self._get_metadata()

        self._save_cache()

    