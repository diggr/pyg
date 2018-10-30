"""
Classes and functions for analyzing the commetator base of youtube channels within Jupyter
Notebooks.

Classes:

* UserList
* ChannelUserList
* User
* Stats

The UserList object loads the complete user list of a pyg (youtube) project (all channels).
By selecting a channel name of the UserList object, a ChannelUserList for a specific channel
can be created.

e.g.
users = UserList()
channel = users["ChannelName"]

Functions:

* venn_diagram


Usage:

Examples on how to use these classes/functions can be found in the 'User Listings Tutorial' 
notebook file.
"""

import sys
import os
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import dateutil.parser
import matplotlib.dates as mdates
from tqdm import tqdm
from matplotlib_venn import venn3, venn2
from itertools import chain
from collections import Counter, defaultdict
from tqdm import tqdm
from ..zip_archive import ZipArchive


def venn_diagram(a, b, c=None):
    """
    Draws a venn diagram of the user lists from two or three ChannelUserList objects
    """
    a_set = set([ x.id for x in a ])
    b_set = set([ x.id for x in b ])
    plt.figure(figsize=(15,15))
    if not c:
        venn2([ set(a_set), set(b_set)], set_labels=(a.channel, b.channel) )
    else:
        c_set = set([ x.id for x in c])
        venn3([ set(a_set), set(b_set), set(c_set)], 
              set_labels=(a.channel, b.channel, c.channel) )        
    plt.show()


def plot_date_hist(dates, title):
    """
    Plots a date-histogram of dates
    """
    data = mdates.date2num(dates)
    fig, ax = plt.subplots(1,1, figsize=(15,8))
    ax.hist(data, bins=100, color='lightblue')
    plt.title(title)
    fig.autofmt_xdate()
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    ax.xaxis.set_minor_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m.%Y'))
    plt.show()     


def _common_user_names(users):
    same_name = defaultdict(set)
    for user in users:
        for name in user.names:
            same_name[name].add(user.id)        
    d = { key: len(value) for key, value in same_name.items () }
    return sorted(d.items(), key=lambda x: -x[1])
    

class ChannelUserList(object):
    """
    Represents a list of all commentators of an Youtube cannel
    """
    def __init__(self, channel, users):
        self.users = users
        self.channel = channel
        self.first_comments_users = [ x for x in self.users if x.first_comment["channel"] == self.channel ]

    def intersect(self, *user_lists):
        """
        Returns the intersection of users with other ChannelUserList objets as a new ChannelUserList object
        """
        #result = set(self.users)
        thislist = set([ x.id for x in self.users ])
        for user_list in user_lists:
            otherlist = set([ x.id for x in user_list])

            thislist = thislist.intersection(otherlist)

        result = [ u for u in self.users if u.id in thislist ]

        return ChannelUserList("intersection", sorted(result, key=lambda x: x.names[0]))

    def __len__(self):
        return len(self.users)

    def __iter__(self):
        for user in self.users:
            yield user

    def common_user_names(self, n=None):
        return _common_user_names(self.users)[:n]

    def by_video(self, video):
        """
        Returns a Counter object of all users and their comments for a specific video
        """
        users = Counter()
        for user in self.first_comments_users:
            count = user.comments_per_video(video)
            if count > 0:
                users[str(user)] += count
        return users

    def stats(self):
        #user_stats = json.load(open(USER_STATS))
        stats = [ x.stats for x in self.users ]
        df = pd.DataFrame(stats)
        df["first_comment_date"] = pd.to_datetime(df["first_comment_date"])
        df["last_comment_date"] = pd.to_datetime(df["last_comment_date"])
        return df


    def first_comment_stats(self):
        #stats = Stats()

        #all_channels = set(chain(*[ u.channels for u in self.users ]))

        print("Channel of first post of each user:")
        print(" ")

        fc = [ u.first_comment for u in self.users]
        df = pd.DataFrame(fc)
        df["channel"].value_counts().plot(kind="bar", figsize=(18,10))
        plt.show()
        print(df["channel"].value_counts())



    def analyze(self):
        """
        Analyzes the user base of a youtube channel:
        * Display the first channel each user posted
        * Plot date histograms of when the users first posted in this channel started posting in other channels.
          And show the average time gap between their inital posts in each channel
        * Show the videos in which the users of this channel started posting in other channels
        """
        stats = Stats()

        channels = []
        for user in self.users:
            channels += user.channels
        channels = set(channels)

        self.first_comment_stats()

        for u in self.users:
            stats.first_channel[u.first_comment["channel"]].append(str(u))

        channel_fc = defaultdict(list)
        channel_vids = defaultdict(Counter)
        channel_distance = defaultdict(list)

        print("Calculating activities in other channels by users first commented in <{}>:".format(self.channel))
        print(" ")


        for u in tqdm(self.first_comments_users):
            for channel in channels:
                if channel in u.comments:
                    first = u.comments[channel]["first_comment"]
                    base = u.comments[self.channel]["first_comment"]
                    base_date = dateutil.parser.parse( base["timestamp"] )

                    date = dateutil.parser.parse( first["timestamp"] )

                    key = "{} -> {}".format(self.channel, channel)
                    channel_distance[key].append(date-base_date)

                    channel_fc[channel].append(date)
                    channel_vids[channel].update([first["video"]])
                    
                    stats.video[first["video"]].append(str(u))
                    comment_count = u.comments[channel]["comments"]
                    if comment_count > 0:
                        stats.succeeding_channel[channel][str(u)] += comment_count

        for key, distance in channel_distance.items():
            mean = np.array(distance).mean()
            print("{}: {} (mean)".format(key, mean))
            median = np.median(distance)
            print("{}: {} (median)".format(key, median))
            print(" ")

 
        for channel_name, dates in channel_fc.items():
            print("Users commented in succeeding channel <{}>: {}".format(channel_name, len(dates)))
            plot_date_hist(dates, channel_name)
            print(" ")

        for channel in channels:
            print(" ")
            print(channel)
            for vid in channel_vids[channel].most_common(30):
                print("\t{}: {}".format(vid[0], vid[1]))

        return stats
   

class Stats(object):
    """
    Return object of the ChannelUserList analyze() function
    """
    def __init__(self):
        self.first_channel = defaultdict(list)
        self.succeeding_channel = defaultdict(Counter)
        self.video = defaultdict(list)


class User(object):
    def __init__(self, id_, stats):
        self.id = id_
        self.comments = stats["comment_stats"]
        self.names = stats["names"]
        self.channels = list(self.comments.keys())
        self.comment_count = stats["total_comments"]
        self.first_comment = {
            "channel": stats["first_comment_channel"],
            "timestamp": stats["first_comment_date"],
            "video": stats["first_comment_video"]
        }
        self.stats = stats

    def __str__(self):
        return "{} [{}]".format(self.names[0], self.id)


class UserList(object):
    def __init__(self, filepath):
        print("loading user data ...")

        self.users = []
        
        if not os.path.exists(filepath):
            raise IOError("User stats file not found")

        archive = ZipArchive(filepath)
        data = archive.get("user_stats.json")
        
        #data = json.load(open(filepath))

        for user_id, stats in tqdm(data.items()):
            self.users.append(User(user_id, stats))
    
    def __getitem__(self, channel):
        users = [ u for u in self.users if channel in u.channels ]
        return ChannelUserList(channel, users)

    def __len__(self):
        return len(self.users)

    def __iter__(self):
        for user in self.users:
            yield user

    def common_user_names(self, n=30):
        return _common_user_names(self.users)[:n]
            
