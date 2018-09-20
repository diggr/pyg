import click
import os
from youtubetools.config import init_project, load_config, fetch_config, network_config
from youtubetools.fetcher import ChannelFetcher, VideoFetcher, ChannelUpdateFetcher
from youtubetools.channel_network import RelatedChannelsNetwork
from youtubetools.video_recommendation_network import VideoRecommendationNetwork
from youtubetools.elasticsearch_ingest import elasticsearch_ingest


@click.group()
def cli():
    """
    pyg command line tool
    """

@cli.command()
def init():
    print("init pyg project")
    init_project()

@cli.command()
@click.argument("group")
def fetch(group):
    fetch_list = fetch_config(group)
    if group == "channels":
        for channel in fetch_list:
            ChannelFetcher(channel=channel)
    else:
        VideoFetcher(fetch_list, group)

@cli.command()
@click.argument("group")
def update(group):
    fetch_list = fetch_config(group)
    if group == "channels":
        for channel in fetch_list:
            ChannelUpdateFetcher(channel=channel)


@cli.command()
@click.argument("network_name")
def network(network_name):
    config = network_config(network_name)
    type_ = config["type"]
    print("\t buliding network <{}>".format(network_name))
    if type_ == "videos":
        q = config["q"] if "q" in config else None
        seeds = config["seeds"] if "seeds" in config else None
        vrn = VideoRecommendationNetwork(
            name=network_name,
            q=q, 
            seeds=seeds, 
            depth=config["depth"])
        vrn.to_graphml()

    elif type_ == "channels":
        cn = RelatedChannelsNetwork(
            name=network_name, 
            seeds=config["seeds"], 
            depth=config["depth"], 
            featured=config["featured"])
        cn.to_graphml()

@cli.command()
@click.argument("group", default="channels")
@click.argument("prefix", default="")
def ingest(group, prefix):
    elasticsearch_ingest(group, prefix)

if __name__ == "__main__":
    cli()
