"""
Build user stats dataset from pyg channel directory

For each user, the following statistics and data are prepared:
- total_comments
- text_len_average
- text_len_median
- first_comment
- last_comment
- total_replies
- replies_per_comments
- comment_count_rank
- reply_count_rank
- channel_stats (comments per channel, first comment in channel)

"""

import os
import json
import numpy as np
import scipy.stats as ss
from collections import defaultdict, Counter
from tqdm import tqdm
from pit.prov import Provenance

from ..reader import YoutubeArchiveReader
from ..config import load_config
from ..zip_archive import ZipArchive

#DATA_DIR = "0../../darksouls/data/channels/"
USER_STATISTICS = "{}_user_stats.zip"

class UserStatsBuilder(object):

    def __init__(self):
        self.CF = load_config()

        self.out_dir = os.path.join(self.CF["PROJECT_DIR"], "analysis")
        if not os.path.exists(self.out_dir):
            os.makedirs(self.out_dir)

        self.channel_dir = os.path.join(self.CF["PROJECT_DIR"], "channels")

        filename = USER_STATISTICS.format(self.CF["PROJECT_NAME"])
        self.stats_file = os.path.join(self.out_dir, filename)

        self.build_user_stats()


    def channel_files(self):
        for channel_file in os.listdir(self.channel_dir):
            if channel_file.endswith(".zip"):    
                filepath = os.path.join(self.channel_dir, channel_file)
                yield filepath, channel_file


    def load_files(self):
        users = defaultdict(list)
        for filepath, filename in self.channel_files():
            channel = YoutubeArchiveReader(filepath=filepath)
            for video in channel:         
                for comment in video.comments:
                    if comment["author_id"]:
                        comment["channel"] = filename.replace(".zip", "")
                        comment["video_id"] = video.id
                        users[comment["author_id"]].append(comment)

        return users        

    def get_first_comment(self, comments, channel):
        comment_list = [ x for x in comments if channel == x["channel"] ] 
        first = sorted(comment_list, key=lambda x: x["timestamp"])[0]
        return {
            "timestamp": first["timestamp"],
            "video": first["video_id"]
        }


    def build_user_stats(self):        

        users = self.load_files()
        user_data = defaultdict(dict)

        #### total comments and avg comment length
        print("building user stats ...")
        for user_id, comments in tqdm(users.items()):
            user_data[user_id]["total_comments"] = len(comments)
            
            comment_lens = [ len(c["text"].split()) for c in comments ]
            
            #comment stats by channel (count, first comment)
            comment_counts = dict(Counter([x["channel"] for x in comments ]))
            channel_stats = defaultdict(dict)
            for channel, count  in comment_counts.items():
                channel_stats[channel]["comments"] = count
                channel_stats[channel]["first_comment"] = self.get_first_comment(comments, channel)
            
            #### total comments and avg comment length
            user_data[user_id]["comment_stats"] = channel_stats
            user_data[user_id]["text_len_average"] = np.array(comment_lens).mean()
            user_data[user_id]["text_len_median"] = np.median(np.array(comment_lens))

            ### first and last comments
            sort_comments = sorted(comments, key=lambda x: x["timestamp"])
            user_data[user_id]["first_comment_channel"] = sort_comments[0]["channel"]
            user_data[user_id]["first_comment_date"] = sort_comments[0]["timestamp"]
            user_data[user_id]["first_comment_video"] = sort_comments[0]["video_id"]
            user_data[user_id]["last_comment_channel"] = sort_comments[-1]["channel"]
            user_data[user_id]["last_comment_date"] = sort_comments[-1]["timestamp"]
            user_data[user_id]["last_comment_video"] = sort_comments[-1]["video_id"]   

            ### replies stats
            count = sum([ x["reply_count"] for x in comments ])
            rp_per_comment = count /  len(comments)
            user_data[user_id]["total_replies"] = count
            user_data[user_id]["replies_per_comments"] = rp_per_comment

            #### user names
            names = set([ x["author"] for x in users[user_id] ])
            user_data[user_id]["names"] = list(names)
            user_data[user_id]["id"] = user_id 


        # rankings
        print("building user rankings ...")

        comment_rank = [ (user_id, x["total_comments"]) for user_id, x in user_data.items() ]
        comment_rank = sorted(comment_rank, key=lambda x: -x[1])

        ranks = ss.rankdata([ -x[1] for x in comment_rank ], method="dense")

        ranking_data = [ x for x in zip(comment_rank, ranks)]
        ranking_dict = { x[0]: r for (x, r) in ranking_data }

        for user_id, rank in ranking_dict.items():
            user_data[user_id]["comment_count_rank"] = int(rank)


        #reply count rankings 

        reply_count = [ (user_id, x["total_replies"]) for user_id, x in user_data.items() ]
        reply_count = sorted(reply_count, key=lambda x: -x[1])

        ranks = ss.rankdata([ -x[1] for x in reply_count ], method="dense")

        ranking_data = [ x for x in zip(reply_count, ranks)]
        ranking_dict = { x[0]: r for (x, r) in ranking_data }

        for user_id, rank in ranking_dict.items():
            user_data[user_id]["reply_count_rank"] = int(rank)


        print("save user stats file ...")

        archive = ZipArchive(self.stats_file, overwrite=True)
        archive.add("user_stats.json", user_data)
        #json.dump(user_data, open(self.stats_file, "w"), indent=4)

        prov = Provenance(self.stats_file)
        prov.add(
            agent="build_pyg_user_stats_script",
            activity="build_user_stats",
            description="user stats from youtube channels in directory <{}>".format(self.channel_dir)
        )
        prov.add_sources([ str(x) for x,y in self.channel_files() ])
        prov.save()
