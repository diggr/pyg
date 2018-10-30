import json
import os
import datetime
import lxml
import re
import html
from bs4 import BeautifulSoup

DATA_DIR="data"

def captions_maxqda_export(channel_name, data_dir=DATA_DIR):
    """
    Transforms the youtube captions xml into a maxqda compatible text file with timestamps
    """
    channel_dir = os.path.join(data_dir, channel_name)
    captions_dir = os.path.join(channel_dir, "video_captions")
    export_dir = os.path.join(channel_dir, "export")
    if not os.path.exists(export_dir):
        os.makedirs(export_dir)
    maxqda_captions_dir = os.path.join(export_dir, "maxqda_captions")
    if not os.path.exists(maxqda_captions_dir):
        os.makedirs(maxqda_captions_dir)

    for filename in os.listdir(captions_dir):
        if ".xml" in filename:
            filepath = os.path.join(captions_dir, filename)
            with open(filepath) as f:
                captions_xml = f.read()

            captions_soup = BeautifulSoup(captions_xml, "lxml")
            lines = []
            for text in captions_soup.find_all("text"):
                #get timestamp
                timestamp_sec = float(text["start"])
                timestamp = str(datetime.timedelta(seconds=timestamp_sec)).replace(".","-")
                #remove html form text
                line_text = text.text
                line_text = re.sub('<[^<]+?>', '', line_text)
                line_text = html.unescape(line_text)
                # bit hacky improve later
                lines.append("#0"+timestamp[:10]+"# "+line_text+"\n")
            
            #save export file
            export_filepath = os.path.join(maxqda_captions_dir, filename.replace(".xml", ".txt"))
            with open(export_filepath, "w") as export_file:
                for line in lines:
                    export_file.write(line)
            
            

    