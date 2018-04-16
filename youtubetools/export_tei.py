from lxml import etree
import os
import json

from .reader import ChannelReader

DATA_DIR = "data"
EXPORT_DIR = "export"

def tei_file(doc_title, content, pub_date):
    """
    Creates barebone TEI xml file and inserts data
    """
    tei = etree.Element("TEI")

    #create header and insert metadata
    tei_header = etree.SubElement(tei, "teiHeader")
    file_desc = etree.SubElement(tei_header, "fileDesc")
    title_stmt = etree.SubElement(file_desc, "titleStmt")
    title = etree.SubElement(title_stmt, "title")
    title.text = doc_title
    publication_stmt = etree.SubElement(file_desc, "publicationStmt")
    publisher = etree.SubElement(publication_stmt, "publisher")
    pub_place = etree.SubElement(publication_stmt, "pubPlace")
    date = etree.SubElement(publication_stmt, "date", when=pub_date)
    source_desc = etree.SubElement(file_desc, "sourceDesc")
    source_p = etree.SubElement(source_desc, "p")

    #create text body and insert content
    text = etree.SubElement(tei, "text")
    text_body = etree.SubElement(text, "body")
    body_p = etree.SubElement(text_body, "p")
    body_p.text = content

    return tei

def generate_tei_corpus(channel_name, data_dir=DATA_DIR, export_dir=EXPORT_DIR):
    """
    Creates TEI corpus of all videos (video captions) in fetched youtube channel and 
    saves resulting xml files to :export_dir:
    """

    #import directories
    caption_dir = os.path.join(data_dir, channel_name, "video_captions")
    metadata_dir = os.path.join(data_dir, channel_name, "video_meta")

    #export directory
    export_dir = os.path.join(export_dir, channel_name, "tei")
    if not os.path.exists(export_dir):
        os.makedirs(export_dir)
    
    for video_file in os.listdir(metadata_dir):
        #prepare import files
        metadata_file = os.path.join(metadata_dir, video_file)
        caption_file = os.path.join(caption_dir, video_file.replace(".json", ".txt"))
        if os.path.exists(caption_file):
            #read youtube captions
            with open(caption_file) as f:
                caption_txt = f.read()
            #read video metadata
            with open(metadata_file) as f:
                metadata = json.load(f)
            title = metadata["items"][0]["snippet"]["title"].replace("/","-")
            date = metadata["items"][0]["snippet"]["publishedAt"][:10]
            #generate and export tei xml file
            tei_xml = tei_file(title, caption_txt, date)
            xml_str = etree.tostring(tei_xml).decode()
            out_file = "{}_{}.xml".format(date, title).replace(" ", "_")
            out_filepath = os.path.join(export_dir, out_file)
            with open(out_filepath, "w") as f:
                f.write(xml_str)