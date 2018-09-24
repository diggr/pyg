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


### Build recommended videos network

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


## Authors:
team@diggr.link

## Lincence:

