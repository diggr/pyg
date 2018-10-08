import click
import os
from youtubetools.config import init_project, load_config, fetch_config, network_config, set_proxy
from youtubetools.fetcher import ChannelFetcher, VideoFetcher, ChannelUpdateFetcher
from youtubetools.channel_network import RelatedChannelsNetwork
from youtubetools.video_recommendation_network import VideoRecommendationNetwork
from youtubetools.elasticsearch_ingest import elasticsearch_ingest

"""
Pyg command line tool

pyg

    --proxy/--no-proxy (default: no-proxy)

    init

    fetch
        <group name>

    update
        <group name>

    network
        <network name>
        --api/--no-api (default: api)

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
        #ctx.obj["PROXY"] = "abc"
    #click.echo(proxy)

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

@cli.command()
@click.argument("group", default="channels")
@click.argument("prefix", default="")
def es(group, prefix):
    elasticsearch_ingest(group, prefix)

@cli.command()
def test():
    click.echo("test")

#if __name__ == "__main__":
#    cli(obj={})
