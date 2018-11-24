"""

Channels statistics script

Counts the number of Videos and Comments of all channels in the dataset.
Saves the result as csv table.

"""

import os
import pandas as pd
from pit.prov import Provenance

from ..zip_archive import ZipArchive
from ..reader import YoutubeArchiveReader
from ..config import load_config, VIDEO_METADATA_DIR, PROV_AGENT


def channel_files(channel_dir):
    for channel_file in os.listdir(channel_dir):
        if channel_file.endswith(".zip"):    
            filepath = os.path.join(channel_dir, channel_file)
            yield filepath, channel_file


def init_analysis_dir(cf):
    out_dir = os.path.join(cf["PROJECT_DIR"], "analysis")
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)    
    return out_dir

def channel_stats():
    CF = load_config()

    out_dir = init_analysis_dir(CF)

    channel_dir = os.path.join(CF["PROJECT_DIR"], "channels")

    videos_total = 0
    comments_total = 0

    stats = []
    filepaths = []

    for filepath, channel_file in channel_files(channel_dir):

        filepaths.append(filepath)

        title = channel_file.replace(".zip", "")
        print(title)

        archive = ZipArchive(filepath)
        channel_meta = archive.get("channel_meta.json")

        videos = channel_meta["items"][0]["statistics"]["videoCount"]
        videos_total += int(videos)
        print("Videos: {}".format(videos))

        video_comments = 0
        for filename in archive[VIDEO_METADATA_DIR]:
            video_meta_file = os.path.join(VIDEO_METADATA_DIR, filename)
            video_meta = archive.get(video_meta_file)
            try:
                video_comments += int(video_meta["items"][0]["statistics"]["commentCount"])
            except:
                print("no comments available for video {}".format(filename))
        print("Comments: {}".format(video_comments))
        comments_total += video_comments

        print("  ")
        stats.append({
            "title": title,
            "videos": videos,
            "comments": video_comments
        })
    
    print("Total videos: {}".format(videos_total))
    print("Total comments: {}".format(comments_total))
    stats.append({
        "title": "Total",
        "videos": videos_total,
        "comments": comments_total
    })

    df = pd.DataFrame(stats)

    stats_file = os.path.join(out_dir, "channel_stats.csv")
    df.to_csv(stats_file, columns=["title", "videos", "comments"], index=False)
    
    prov = Provenance(stats_file)
    prov.add(
        agent=PROV_AGENT,
        activity="analysis_channel_stats",
        description="generate list of videos and comments for channels in <{}>".format(channel_dir)
    )
    prov.add_sources(filepaths)
    prov.save()

