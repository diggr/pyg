# pyg - passable youtube grabber

![Python 3]( https://img.shields.io/badge/python-3.5%20%7C%203.6%20%7C%203.7-blue.svg)

*pyg* is a wrapper around the Youtube-API, and allows easy retrieval and analysis
of specific data.

> You need a working Youtube-API key in order to use this program. See the [Google Developers Portal](https://developers.google.com/youtube/v3/getting-started) for more information on how to create one. 

![pyg logo](assets/pyg_logo.png?raw=true "pyg")

## Features
 
- Fetch Youtube data (metadata for videos, playlists, comments and captions) for channels as well as for collections of videos
- Export data to Elasticsearch (videos and comments)
- Build networks of recommended videos
- Saves networks as .graphml files (can be imported into Gephi)

## Requirements

- Python >3.5 
- a Youtube API v3 key
- a running Elasticsearch instance *optional*

## Installation

Clone this repository and install it (preferably into a virtualenv):

```zsh
$ git clone https://github.com/diggr/pyg
$ cd pyg
$ pip install .
```

## Quickstart

Create a project folder and initialize project there:

```zsh
$ mkdir pygproject
$ cd pygproject
$ pyg init

```

The last command creates template files for the project configuration (config.yml), fetch items (channels.yml, videos.yml) and networks (network.yml). 

### Configuration

Before you can start, you will need to add some information to the config.yml. Enter your Youtube API and credentials for your elasticsearch server key into the *config.yml* in order to proceed (the latter can be left blank if you don't intend to export to ES.

```yaml
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

### Fetching Channels

The main configuration file (contentwise) is the *channels.yml* file in the root directory.
It contains a list of all channel identifiers to be fetched. 

Note: The channels can be grouped, to allow for a granular retrieval and update process.

```yaml
main_group:
  - channel/UCdQHEqTxcFzjFCrq0o4V7dg
  - channel/UCI06ztiuPl-F9cSXsejMV8A
other_group:
  - channel/UCZzPA6tCoQAZNiddpE-xA_Q
```

After filling in your preferred chanels, run the fetch command to fetch the data using
the Youtube API:

```zsh
$ pyg fetch channels
```

If you are interested in only a specific group, you can give it a argument:

```
$ pyg fetch channels other_group
```

The channels will be fetched and saved into the projects data folder (which is specified in the previously configured *config.yml*) Each groups contents will be stored in a separate folder, and each channel in a separate zip archive (See e.g. [olf42/zip_archive](https://github.com/olf42/zip_archive) for a small zip file wrapper in Python). 

Additonally provenance information is recorded an stored next to the zip files. The provenance information is stored in JSON-LD using the W3C PROV-O ontology. See [diggr/provit](https://github.com/diggr/provit) for more information about recording, reading and processing provenance information.

### Fetching Videos

It is also possible to just get single videos in a similar way. Add the videos IDs to your *videos.yml*:

```yaml
my_video_list:
  - 5IsSpAOD6K8
  - qFLw26BjDZs
```

and use the fetch videos command:

```zsh
$ pyg fetch videos 
```

or for a specific group:

```zsh
$ pyg fetch videos my_video_list
```

### Search

You can search youtube an get a result list, which is ready to be pasted into the `videos.yml` file.

```zsh
$ pyg search diggr --results 50
```

The `--results` flag sets the number of results (max: 50, default: 10).


### Export to elasticsearch

The video and channel data can be exported to an elasticsearch instance to ease further
processing and investigation of the fetched data. The *export* command will build a 
separate index for each data type (video related data and comment related data).
If not specified otherwise, it will use the prefix defind in the *config.yaml*

The following command will build two indices:
pyg\_videos
pyg\_comments

```zsh
$ pyg elasticsearch channels
```

The following command build two indices:
my\_prefix\_videos
my\_prefix\_comments

```
$ pyg elasticsearch channels other\_group my\_prefix
```

> CAUTION: If an index already exists, it will be overwritten!


### Fetching Updates 

You can use the integrated update function to fetch new comments, videos and channels:

```zsh
$ pyg update channels
```

The update script checks for each video in the channel if the comment count changed. If so, the current video data will be fetched from the Youtube API.
New videos will also fetched.

An update-file for each channel in the form of <channel_name>_<timestamp>.zip will be created in the data folder.


### Build recommended videos networks

Add your network configuration to the *network.yml*:

```yaml
darksouls:
  type: 'videos'
  q: 'dark souls'
  depth: 2
```

By using the *network* command, you can create a graphml file, which can be used in Gephi
or similar tools to be investigated.

```zsh
$ pyg network darksouls
```

### Usage behind a proxy Server

List proxy in config.yml

```yaml
network:
  proxy: 123.4.5.6:7890
```

You are required to give the *--proxy* option in order to use the given proxy.

```
$ pyg --proxy network darksouls
```

## Command line interface

```zsh
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

## Copyright
- 2019, Universitätsbibliothek Leipzig <info@ub.uni-leipzig.de>

## Authors
- P. Mühleder <muehleder@ub.uni-leipzig.de>
- F. Rämisch <raemisch@ub.uni-leipzig.de>

## Licence
- GNU General Public License v3 (Software)
- CC-BY (Assets)
