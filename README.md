# Pyg - passable youtube grabber

- Fetch Youtube channel data (metadata for videos, playlists, comments; comment data and captions - if available)
- Export Youtube channel data to elasticsearch index
- Build network of related Youtube channels
- Build network of recommended videos

## Install:

Download git repo

```
pip install .

```

### Requirements:

- Python 3.6
- Youtube Data API Key


## Usage:

```
pyg init
#builds config/fetch/network.yml templates

pyg fetch
#fatches all channels specified in fetch.yml

pyg build-networks
#builds all network graphs (as graphml) specified in network.yml

```

## Authors:
team@diggr.link

## Lincence:
Best-license-ever
