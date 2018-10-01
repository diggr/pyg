# Pyg - passable youtube grabber

A tool for Youtube data retrieval and analysis.

## Functionality:
 
* Fetch Youtube data (metadata for videos, playlists, comments and captions) for channels as well as for collections of videos
* Export data to Elasticsearch (videos and comments)
* Build networks of related channels or recommended videos
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
The last command creates template files for the project configuration (config.yml), fetch items (fetch.yml) and networks (network.yml).

### Configure project

Open config.yml and add:
* Youtube API key
* Url with user name and password of the elasticsearch server / prefix for the video/comment index (can be left blank if you don't intend of exporting data to ES)
* Project name (not used at the moment)

### Fetch youtube data

Add fetch items (channels or video lists) to fetch.yml

e.g. fetch.yml:
```
channels:
- channel/UCdQHEqTxcFzjFCrq0o4V7dg
- channel/UCI06ztiuPl-F9cSXsejMV8A
```


Then use the pyg fetch command

```
$ pyg fetch channels
```


Ingest youtube data to elasticsearch

```
$ pyg ingest channels
```


Generate Diff file 

```
$ pyg update channels
```

The update script checks for each video in the channel if the comment count changed. If so, the current video data will be fetched from the Youtube API.
New videos will also fetched.

A Diff file for each channel in the form of <chanel_name>_timestamp.zip will be created in the data folder.


### Build recommended videos and related channel networks

Add network configuration to network.yml

e.g. network.yml
```
darksouls:
  type: 'videos'
  q: 'dark souls'
  depth: 2


mgs:
  type: 'channels'
  seeds:
  - 'channel/UCT6iAerLNE-0J1S_E97UAuQ'
  - 'user/pythonselkanHD'
  featured: false
  depth: 5  
```

Then use the pyg network command to build the network graphml file

```
$ pyg network darksouls
```

```
& pyg network mgs
```


## Authors:
team@diggr.link

## Lincence:

