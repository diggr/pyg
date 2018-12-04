import click
import os
from .config import init_project, load_config, channel_config, video_config, network_config, set_proxy
from .fetcher import ChannelFetcher, VideoFetcher, ChannelUpdateFetcher
from .channel_network import RelatedChannelsNetwork
from .video_recommendation_network import VideoRecommendationNetwork
from .elasticsearch_ingest import elasticsearch_ingest
from .analysis import UserStatsBuilder, channel_stats
from .utils import get_channel_files

"""
Pyg command line tool

pyg

    --proxy/--no-proxy (default: no-proxy)

    init

    fetch
        <group name>
        --comments/--no-comments (fetch comments; default: comments)
        --captions/--no-captions (fetch captoins; default: captoins)
        --skip/--no-skip (skip already fetched channels: default: skip)

    update
        <group name>

    network
        <network name>
        --api/--no-api (default: api)
    
    analysis
        <analysis type>

    es
        <group name>
        <index prefix>

"""

@click.group()
@click.option("--proxy/--no-proxy", default=False)
@click.pass_context
def cli(ctx, proxy):
    """
    pyg command line tool
    """
    if proxy:
        c = load_config()
        url = c["PROXY"]
        ctx.obj = { "PROXY": url}


# INIT COMMAND

@cli.command()
def init():
    print("init pyg project")
    init_project()


# FETCH COMMANDS

@cli.group()
def fetch():
    pass

@fetch.command()
@click.argument("group", default="all")
@click.option("--comments/--no-comments", default=True)
@click.option("--captions/--no-captions", default=True)
@click.option("--skip/--no-skip", default=True)
def channels(group, comments, captions, skip):
    for group_name, channels in channel_config():
        print(group_name, channels)
        if group == "all" or group_name == group:
            for channel in channels:
                ChannelFetcher(channel=channel, captions=captions, comments=comments, skip=skip, group=group_name)

@fetch.command()
@click.argument("group", default="all")
@click.option("--comments/--no-comments", default=True)
@click.option("--captions/--no-captions", default=True)
@click.option("--skip/--no-skip", default=True)
def videos(group, comments, captions, skip):
    for group_name, video_ids in video_config():
        if group == "all" or group_name == group:
            VideoFetcher(video_ids, group_name)


# UPDATE COMMAND

@cli.group()
def update():
    pass

@update.command()
@click.argument("group", default="all")
def channels(group):
    CF = load_config()
    for channel_cf  in get_channel_files(CF):
        archive_name = channel_cf["archive_name"].replace(".zip", "")
        archive_filepath = channel_cf["archive"]
        print(archive_name, archive_filepath)
        ChannelUpdateFetcher(archive_name, archive_filepath)
    # for group_name, channels in channel_config():
    #     print(group_name, channels)
    #     if group == "all" or group_name == group:
    #         for channel in channels:
    #             ChannelUpdateFetcher(channel=channel)


# NETWORK COMMAND

@cli.command()
@click.option("--api/--no-api", default=True)
@click.argument("network_name")
@click.pass_context
def network(ctx, api, network_name):
    if ctx.obj:
        click.echo("set proxy to: {}".format(ctx.obj["PROXY"]))
        set_proxy(ctx.obj["PROXY"])
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
            api=api,
            depth=config["depth"])
        vrn.to_graphml()

    elif type_ == "channels":
        cn = RelatedChannelsNetwork(
            name=network_name, 
            seeds=config["seeds"], 
            depth=config["depth"], 
            featured=config["featured"])
        cn.to_graphml()




# ANALYSIS COMMAND

@cli.command()
@click.argument("analysis_type", default="channels")
def analysis(analysis_type):
    if analysis_type == "user-stats":
        stats = UserStatsBuilder()
    elif analysis_type == "channel-stats":
        channel_stats()


# ELASTICSEARCH EXPORT COMMANDS

@cli.group()
def elasticsearch():
    pass

@elasticsearch.command()
@click.argument("group", default="all")
@click.argument("prefix", default="")
def channels(group, prefix):
    elasticsearch_ingest(group, prefix)
    print("es cahnnels")

@elasticsearch.command()
@click.argument("group", default="all")
@click.argument("prefix", default="")
def videos(group, prefix):
    elasticsearch_ingest(group, prefix, is_video_list=True)
    print("es videos")



