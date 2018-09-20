import os
import zipfile
from tqdm import tqdm 
from youtubetools.reader import ChannelReader
from youtubetools.fetcher import VideoFetcher, ChannelFetcher


#cr = ChannelReader("/home/pmuehleder/data/youtube-counterpublics/data/channels/NuoViso.TV.zip")
#print(cr.videos[1].users())
# channel_dir = "/home/pmuehleder/data/youtube/YongYea"
# #export_dir 
# channel_name = "test.zip"

# def archive_channel():
#     """
#     Archives youtube channel into compressed zip file
#     """
#     with zipfile.ZipFile(channel_name, "w", zipfile.ZIP_DEFLATED) as zf:
#         for filepath, dirs, files in os.walk(channel_dir):
#             print("\t compress {}".formatTTTT(filepath))
#             for file_name in files:
#                 source_filepath = os.path.join(filepath, file_name)
#                 zf.write(source_filepath, os.path.relpath(source_filepath, channel_dir))

# archive_channel()

#fetcher = VideoFetcher(["rVMTWgAgVfs", "B5P_eB7a32c"])
fetcher = ChannelFetcher("channel/UCT6iAerLNE-0J1S_E97UAuQ")
