"""
Initializes and loads project yaml files:

- config.yml: project directory, youtube api key, elasticsearch credentials
- fetch.yml: list of youtube channels to fetch
- network.yml: specifies related channel/recommended video channels
"""

import yaml
import os
import json
import socks
import socket

__VERSION__ = 1.0

PROV_AGENT = "pyg_{}".format(__VERSION__)


#YAML TEMPLATES
NETWORK_TEMPLATE = """
# mgs:
#   type: 'videos'
#   q: 'metal gear solid'
#   depth: 1
#
# yy_thegift:
#   type: 'videos
#   seeds:
#   - 'Fg1EvKUhZw4'
#   depth: 3
#
# yongyea:
#   type: 'channels'
#   seeds:
#   - 'channel/UCT6iAerLNE-0J1S_E97UAuQ'
#   - 'user/pythonselkanHD'
#   featured: false
#   depth: 5    
"""

FETCH_TEMPLATE = """
# channels:
# - 'user/pythonselkanHD'
# - 'channel/UCT6iAerLNE-0J1S_E97UAuQ'
"""

FETCH_CHANNELS_TEMPLATE = """
# main:
# - 'user/pythonselkanHD'
# - 'channel/UCT6iAerLNE-0J1S_E97UAuQ'
"""

FETCH_VIDEOS_TEMPLATE = """
# video_list:
# - '5IsSpAOD6K8'
"""


#DATA DIRECTORIES
DATA_DIR = "data"
ADDON_DIR = "addon"

#ARCHIVE DIRECTORIES
VIDEO_CAPTIONS_DIR = "video_captions"
VIDEO_COMMENTS_DIR = "video_comments"
VIDEO_METADATA_DIR = "video_meta"
PLAYLISTS_DIR = "playlists"


def init_project():
    """
    Creates templates for config.yml, fetch.yml, network.yml
    """

    config = {
        "project": {
            "name": "pyg_project",
            "dir": "data"
        },
        "network": {
            "proxy": ""
        },
        "youtube": {
            "api-key": ""
        },
        "elasticsearch" : {
            "url": "",
            "prefix": "pyg_"
        }
    }
    if not os.path.exists("config.yml"):
        with open("config.yml", "w") as f:
            yaml.dump(config, f, default_flow_style=False)

    if not os.path.exists("channels.yml"):
        with open("channels.yml", "w") as f:
            f.write(FETCH_CHANNELS_TEMPLATE)

    if not os.path.exists("network.yml"):
        with open("network.yml", "w") as f:
            f.write(NETWORK_TEMPLATE)

    if not os.path.exists("videos.yml"):
        with open("videos.yml", "w") as f:
            f.write(FETCH_VIDEOS_TEMPLATE)

def load_config():
    """
    load config yml project directory and youtube api key information
    """
    try:
        with open("config.yml") as f:
            config = yaml.safe_load(f)
        PROJECT = config["project"]
        PROJECT["dir"]
        YOUTUBE_API_KEY = config["youtube"]["api-key"]
        PROXY = config["network"]["proxy"]
    except:
        PROJECT = {}
        PROJECT["dir"] = ""
        YOUTUBE_API_KEY = ""

    if YOUTUBE_API_KEY == "" or PROJECT["dir"] == "":
        raise IOError("config.yml not configured correctly")

    config = {
        "PROJECT_DIR": PROJECT["dir"],
        "YOUTUBE_API_KEY": YOUTUBE_API_KEY,
        "ADDON_DIR": os.path.join(PROJECT["dir"], ADDON_DIR),
        "PROJECT_NAME": PROJECT["name"],
        "PROXY": PROXY
    }
    return config


def load_elasticsearch_config():
    """
    load elasticsearch credentials and index prefix from config.yml
    """
    try:
        with open("config.yml") as f:
            config = yaml.safe_load(f)
    except:
        raise IOError("config.yml not there ...")

    try:
        es_config = config["elasticsearch"]
        url = es_config["url"]
        prefix = es_config["prefix"]
        ES_SERVER = url
        
        if prefix == "":
            raise IOError("es index prefix needed in config.yml")

        return ES_SERVER, prefix

    except:
        raise IOError("config.yml not valid")


def channel_config():
    """
    yields all channel in channels.yml
    """
    try:
        with open("channels.yml") as f:
            fetch = yaml.safe_load(f)
    except:
        raise IOError("No valid channels.yml available")
    
    for group, channels in fetch.items():
        yield (group, channels)


def video_config():
    try:
        with open("videos.yml") as f:
            fetch = yaml.safe_load(f)
    except:
        raise IOError("No valid videos.yml available")
    print(fetch)
    for group, video_ids in fetch.items():
        yield (group, video_ids)

def network_config(network_name):
    """
    yields all network graph specifications in network.yml
    """
    try:
        with open("network.yml") as f:
            network = yaml.safe_load(f)
    except:
        raise IOError("network.yml does not exist")

    for name, config in network.items():
        if network_name == name:
            return config

    raise IOError("no config for network <{}> available".format(network_name)) 


def set_proxy(proxy):
    """
    sets up proxy connection
    """
    addr, port = proxy.split(":")
    socks.setdefaultproxy(proxy_type=socks.PROXY_TYPE_SOCKS5, addr=addr, port=int(port))
    socket.socket = socks.socksocket