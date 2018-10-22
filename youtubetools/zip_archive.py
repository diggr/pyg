"""
Simple Zip archvie.
Writes json/text files into zip file.
Reads files from zip file

Usage

z = ZipArchive("test.zip")

y = { ... }

if not z.contains("y.json"):
    z.add("y.json", y)

...

y = z.get("y.json")

"""

import zipfile
import json
import os
from pit.prov import Provenance

class ZipArchive(zipfile.ZipFile):

    def __init__(self, filepath, overwrite=False):
        self.filepath = filepath
        if not os.path.exists(filepath) or overwrite:
            super().__init__(filepath, "w", zipfile.ZIP_DEFLATED)
        else:
            super().__init__(filepath, "a", zipfile.ZIP_DEFLATED)

    def add(self, filepath, data):
        """
        Add data (str, data or list) to zip file.
        """
        if isinstance(data, list) or isinstance(data, dict):
            data = json.dumps(data, indent=4)
        elif not isinstance(data, str):
            raise TypeError("Ziparchive only supports datatypes string, list and dict")
        self.writestr(filepath, data)    
    
    # def remove(self, filepath):
    #     """
    #     very ugly hack, find another way!
    #     only works under linux
    #     removes file from zip archive
    #     """
    #     cmd = ['zip', '-d', self.filename, filepath]
    #     subprocess.check_call(cmd)

    def get(self, filepath):
        """
        Reads (text-)file from zip file.
        """
        data = self.read(filepath)
        if filepath.endswith(".json"):
            return json.loads(data.decode("utf-8"))
        else:
            return data.decode("utf-8")       

    def contains(self, filepath):
        """
        Check if zip file contains file :filepath:
        """
        if filepath in self.namelist():
            return True
        else:
            return False

    def add_provenance(self, agent, activity, description):
        prov = Provenance(self.filepath)
        prov.add(
            agent=agent, 
            activity=activity, 
            description=description)
        prov.add_primary_source("youtube", url="https://www.youtube.com")
        prov.save()   

    def __iter__(self):
        for filename in self.namelist():
            yield filename
    
    def __getitem__(self, directory):
        for filename in self:
            if filename.startswith(directory+"/"):
                yield filename[len(directory)+1:]
