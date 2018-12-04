import os
import json
from tqdm import tqdm
from elasticsearch.exceptions import ConnectionTimeout
from elasticsearch import helpers
from elasticsearch import Elasticsearch
from .reader import YoutubeArchiveReader
from .config import load_elasticsearch_config, load_config, ADDON_DIR, VIDEO_CAPTIONS_DIR, VIDEO_COMMENTS_DIR
from .utils import get_channel_files, get_video_files

VIDEO_INDEX = "{prefix}_yt_videos"
VIDEO_DOC_TYPE = "video"
VIDEO_MAPPING = {
    "video": {
        "properties" : {
            "id": {"type": "keyword"},
            "channel": {"type": "keyword"},
            "channel_group": {"type": "keyword"},
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
            "channel_group": {"type": "keyword"},            
            "video_id": { "type": "keyword" },
            "video_title": { "type": "text" },
            "video_playlists": {"type": "keyword"},
            "classifiers": {
                "type": "keyword"
            },            
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


def load_comment_classifier(cf):
    """
    Loads additional comment classifiers (e.g. through labeling) form  the ADDON data directory
    """
    filepath = os.path.join(cf["ADDON_DIR"], "{}_comment_classifier.json".format(cf["PROJECT_NAME"]))
    if os.path.exists(filepath):
        return json.load(open(filepath))
    else:
        return None
    
def get_classifiers(classifier_dict, id_):
    if classifier_dict:
        if id_ in classifier_dict:
            return classifier_dict[id_]
    return None


def elasticsearch_ingest(group, costum_prefix="", is_video_list=False):
    """
    Imports channel :channel_name: into elasticsearch
    """
    CF = load_config()
    ES_SERVER, prefix = load_elasticsearch_config()

    if costum_prefix:
        prefix = costum_prefix

    #import additonal comment classification
    comment_classfifier =  load_comment_classifier(CF)

    video_index = VIDEO_INDEX.format(prefix=prefix)
    comment_index = COMMENT_INDEX.format(prefix=prefix)

    if ES_SERVER:
        es = Elasticsearch(ES_SERVER)
    else:
        es = Elasticsearch()
    
    _init_es(es, prefix, video_index, comment_index)

    if not is_video_list:
        archives = get_channel_files(CF)
    else:
        archives = get_video_files(CF)

    if group != "all":
        archives = [ x for x in archives if x["group"] == group ]

    for archive_config in archives:
        archive_filepath = archive_config["archive"]
        channel_group = archive_config["group"]

        print("import youtube archive <{}> into elasticsearch".format(archive_filepath.split("/")[-1]))

        archive = YoutubeArchiveReader(archive_filepath)

        # tqdm does not work atm
        for i, video in enumerate(archive):
            channel = video.channel

            print(i)

            video_playlists = [x["title"] for x in video.playlists]
            try:
                caption = video.caption()
            except:
                caption = None
            if caption:
                caption_len = len(caption.split())
            else:
                caption_len = 0

            doc = {
                "id": video.id,
                "title": video.title,
                "channel": channel,
                "channel_group": channel_group,
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

            while True:
                try:
                    res = es.index(index=video_index, doc_type=VIDEO_DOC_TYPE, id=video.id, body=doc)
                except ConnectionTimeout:
                    continue
                break

            comments_doc = []
            for comment in video.comments:
                top_level_comment = True if "." in comment["id"] else False

                if comment["text"]:
                    text_len = len(comment["text"].split())
                else:
                    text_len = 0

                classifiers = get_classifiers(comment_classfifier, comment["id"])

                comments_doc.append({
                    "_index": comment_index,
                    "_type": COMMENT_DOC_TYPE,
                    "_id": comment["id"],
                    "_source": {
                        "video_id": video.id,
                        "channel": channel, 
                        "channel_group": channel_group,
                        "video_title": video.title,
                        "video_playlists": video_playlists,
                        "classifiers": classifiers,
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
            while True:
                try:
                    helpers.bulk(es, comments_doc)
                except ConnectionTimeout:
                    continue
                break

    




