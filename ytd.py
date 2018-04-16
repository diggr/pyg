import os
import sys
import yaml
import click
from youtubetools.config import init, load_config, fetch_queue, network_queue
from youtubetools.fetcher import ChannelFetcher
from youtubetools.channel_network import RelatedChannelsNetwork
from youtubetools.video_recommendation_network import VideoRecommendationNetwork
from youtubetools.elasticsearch_ingest import elasticsearch_ingest


def fetch():
    """
    fetches youtube channels in fetch.yml
    """
    for channel in fetch_queue():
        fetcher = ChannelFetcher(channel=channel)
        fetcher.get_channel_comments()
        fetcher.get_playlists()
        fetcher.get_video_metadata()
        fetcher.get_video_comments()
        fetcher.get_video_captions()        
        fetcher.archive_channel()

def elasticsearch_export():
    """
    builds elasticsearch indexes with channel/video/comments information
    """
    #build_es_index()
    raise NotImplementedError

def channel_user_networks():
    """
    builds user network based on video comments for channels spezified in network.yml
    """
    raise NotImplementedError

def video_networks():
    """
    builds video networks with seeds from network.yml
    """
    for name, config  in network_queue("videos"):

        print("\t buliding network <{}>".format(name))

        q = config["q"] if "q" in config else None
        seeds = config["seeds"] if "seeds" in config else None
        
        vrn = VideoRecommendationNetwork(
            name=name,
            q=q, 
            seeds=seeds, 
            depth=config["depth"])
        vrn.to_graphml()

def channel_networks():
    """
    builds video networks with seeds from network.yml
    """
    for name, config in network_queue("channels"):
        print("\t buliding network <{}>".format(name))
        cn = RelatedChannelsNetwork(
            name=name, 
            seeds=config["seeds"], 
            depth=config["depth"], 
            featured=config["featured"])
        cn.to_graphml()
 
@click.command()
@click.argument("process")
def main(process):
    if process == "init":
        print("init project ...")
        init()
    if process == "fetch":
        print("fetching youtube channels ...")
        fetch()
    if process == "build-networks":
        print("building channel network files ...")
        channel_networks()
        print("building video networks files ...")
        video_networks()
    if process == "elasticsearch-ingest":
        elasticsearch_ingest()
        



