# PYG - passable youtube grabber

A tool for Youtube data retrieval and analysis.

Current version: 1.0.0

## Functionality:
 
* Fetch Youtube data (metadata for videos, playlists, comments and captions) for channels as well as for collections of videos
* Export data to Elasticsearch (videos and comments)
* Build networks of recommended videos
* Saves networks as .graphml files (can be imported into Gephi)

## Install:

Download git repo

```
pip install .

```

### Requirements:

- Python 3.6
- Youtube Data API Key

## Usage:

1. Generate project folder and initialize project

```
$ mkdir pygproject
$ cd pygproject
$ pyg init

```
The last command creates template files for the project configuration (config.yml), fetch items (channels.yml, videos.yml) and networks (network.yml).


### Command line interface

```
pyg

    --proxy/--no-proxy (default: no-proxy)

    init

    fetch
        channels
            <group name>
            --comments/--no-comments (default: comments)
            --captions/--no-captions (default: captions)
        videos
            <group name>
            --comments/--no-comments (default: comments)
            --captions/--no-captions (default: captions)

    update
        channels
            <group name>

    network
        <network name>
        --api/--no-api (default: api)

    analysis
        user-stats
        channel-stats

    elasticsearch
        channels
            <group name>
            <index prefix>
        videos
            <group name>
            <index prefix>
```

### The config.yml

Before you can start, you will need to add some information to the config.yml.
At least you need:
* Youtube API key
* Url (with user name and password) of your elasticsearch server (can be left blank if you don't intend to export data to ES)

```
elasticsearch:
  prefix: pyg_        # default elasticsearch prefix
  url: ''             # url for elasticsearch server
network:
  proxy: ''           # if you use a proxy server, add it here
project:         
  dir: data           # you might change the data directory (or not)
  name: pyg_project   # change to your project name
youtube:
  api-key: ''         # add your YouTube API key here, otherwise nothing will work
```



### Fetch youtube data

Add fetch items (channels) to channels.yml

```
main_group:
- channel/UCdQHEqTxcFzjFCrq0o4V7dg
- channel/UCI06ztiuPl-F9cSXsejMV8A
other_group:
- channel/UCZzPA6tCoQAZNiddpE-xA_Q
```

Then use the pyg fetch command

```
$ pyg fetch channels
```

or for only a specific group:

```
$ pyg fetch channels other_group
```

The channels will be fetched and saved into the projects data folder (specified in the config.yml). 
For each group, a folder will be created where each channel in the group will be saved as a zip archive. 
Pyg will also generate a .prov file for each zip archive, containing metadata about the fetching process.


It is also possible to just get single videos in a similar way.

Add the videos IDs to videos.yml:

```
my_video_list:
- 5IsSpAOD6K8
- qFLw26BjDZs
```

and use the fetch videos command:

```
$ pyg fetch videos 
```

or for a specific group:

```
$ pyg fetch videos my_video_list
```


### Ingest youtube data to elasticsearch

This command build two elasticsearch indexes, one for the video data and one for comment data.
If not otherwise specified, it will use the prefix defind in the config.yaml

The following command build two indexes:
pyg_videos
pyg_comments

```
$ pyg elasticsearch channels
```


The following command build two indexes:
my_prefix_videos
my_prefix_comments

```
$ pyg elasticsearch channels other_group my_prefix
```

CAUTION: If an index already exists, it will be overwritten!


Video lists work in the same way:

```
$ pyg elasticsearch videos my_video_list
```

Again, be careful not to overwrite existing indexes.


### Get channel updates 

```
$ pyg update channels
```

The update script checks for each video in the channel if the comment count changed. If so, the current video data will be fetched from the Youtube API.
New videos will also fetched.

An update-file for each channel in the form of <channel_name>_<timestamp>.zip will be created in the data folder.


### Build recommended videos networks

Add network configuration to network.yml

e.g. network.yml
```
darksouls:
  type: 'videos'
  q: 'dark souls'
  depth: 2

```

Then use the pyg network command to build the network graphml file

```
$ pyg network darksouls
```

```
$ pyg network mgs
```

### Run pyg through a proxy server

List proxy in config.yml

```
...
network:
  proxy: 123.4.5.6:7890
...
```

Use proxy option

```
$ pyg --proxy network darksouls
```

### TODO

- Update video lists


## Authors:
team@diggr.link

## Licence:
GPL-3.0
