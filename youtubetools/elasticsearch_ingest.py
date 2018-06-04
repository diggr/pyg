from elasticsearch import Elasticsearch
from .reader import ChannelReader
import os
from tqdm import tqdm
from elasticsearch import helpers
from .config import load_elasticsearch_config, load_config

VIDEO_INDEX = "{prefix}_yt_videos"
VIDEO_DOC_TYPE = "video"
VIDEO_MAPPING = {
    "video": {
        "properties" : {
            "id": {"type": "keyword"},
            "channel": {"type": "keyword"},
            "title": {"type": "text"},
            "description": {"type": "text"},
            "publication_date": {
                "type": "date"
            },
            "tags": { 
                "type": "keyword",
            },
            "categories": { 
                "type": "keyword",
            },
            "playlists": { "type": "keyword" },
            "duration": { "type": "integer"},
            "views": { "type": "integer" },
            "likes": { "type": "integer" },
            "dislikes": { "type": "integer"},
            "favorites": { "type": "integer" },
            "comment_count": { "type": "integer" },
            "caption": { "type": "text" },
            "caption_len": { "type": "integer" },
            "users": { 
                "type": "keyword"
            }
        }
    },
}

COMMENT_INDEX = "{prefix}_yt_comments"
COMMENT_DOC_TYPE = "comment"
COMMENT_MAPPING = {
    "comment": {
        "properties": {
            "channel": {"type": "keyword"},
            "video_id": { "type": "keyword" },
            "video_title": { "type": "text" },
            "video_playlists": {"type": "keyword"},
            "user": { "type": "keyword"},
            "user_id": { "type": "keyword" },
            "likes": { "type": "integer"},
            "text": { "type": "text"},
            "text_len": {"type": "integer"},
            "reply_count": { "type": "integer" },
            "comment_thread": { "type": "keyword" },
            "timestamp": { "type": "date" },
            "top_level_comment": {"type": "boolean"}
        }
    }
}

def _init_es(es, prefix, video_index, comment_index):
    """
    sets up blank es index and adds doc type mapping information
    """
    if es.indices.exists(index=video_index):
        es.indices.delete(index=video_index)
    if es.indices.exists(index=comment_index):
        es.indices.delete(index=comment_index)  
    
    es.indices.create(video_index)
    es.indices.put_mapping(index=video_index, doc_type=VIDEO_DOC_TYPE, body=VIDEO_MAPPING)

    es.indices.create(comment_index)
    es.indices.put_mapping(index=comment_index, doc_type=COMMENT_DOC_TYPE, body=COMMENT_MAPPING)

def elasticsearch_ingest():
    """
    Imports channel :channel_name: into elasticsearch
    """
    CF = load_config()
    ES_SERVER, prefix = load_elasticsearch_config()

    video_index = VIDEO_INDEX.format(prefix=prefix)
    comment_index = COMMENT_INDEX.format(prefix=prefix)

    if ES_SERVER:
        es = Elasticsearch(ES_SERVER)
    else:
        es = Elasticsearch()
    #print(video_index)
    
    _init_es(es, prefix, video_index, comment_index)

    channel_dir = os.path.join(CF["PROJECT_DIR"], "channels")
    for file_name in os.listdir(channel_dir):
        if ".prov" not in file_name:
            channel = file_name.replace(".zip", "").strip()
            print("import channel <{}> into elasticsearch".format(channel))

            yy = ChannelReader(channel)

            for i, video in tqdm(enumerate(yy.videos)):

                video_playlists = [x["title"] for x in video.playlists]

                caption = video.caption()
                if caption:
                    caption_len = len(caption.split())
                else:
                    caption_len = 0

                doc = {
                    "id": video.id,
                    "title": video.title,
                    "channel": channel,
                    "caption_len": caption_len, 
                    "description": video.description,
                    "publication_date": video.pub_date[:10],
                    "tags": video.tags,
                    "categories": video.categories,
                    "views": video.views,
                    "likes": video.likes,
                    "dislikes": video.dislikes,
                    "favorites": video.favorites,
                    "comment_count": video.comment_count,
                    "caption": caption,
                    "users": video.users(),
                    "duration": video.duration,
                    "playlists": video_playlists
                }
                res = es.index(index=video_index, doc_type=VIDEO_DOC_TYPE, id=video.id, body=doc)

                comments_doc = []
                for comment in video.comments:
                    top_level_comment = True if "." in comment["id"] else False

                    if comment["text"]:
                        text_len = len(comment["text"].split())
                    else:
                        text_len = 0

                    comments_doc.append({
                        "_index": comment_index,
                        "_type": COMMENT_DOC_TYPE,
                        "_id": comment["id"],
                        "_source": {
                            "video_id": video.id,
                            "channel": channel, 
                            "video_title": video.title,
                            "video_playlists": video_playlists,
                            "user": comment["author"],
                            "user_id": comment["author_id"],
                            "text": comment["text"],
                            "text_len": text_len,
                            "reply_count": comment["reply_count"],
                            "comment_thread": comment["comment_thread"],
                            "timestamp": comment["timestamp"],
                            "likes": comment["likes"],
                            "top_level_comment": top_level_comment
                        }
                    })
                helpers.bulk(es, comments_doc)
    

