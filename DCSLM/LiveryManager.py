from . import Livery
from .UnitConfig import Units
import os, sys
import json

DCSLMFolderName = "DCSLM_Root"

class LiveryManager:
  def __init__(self):
    self.LiveryData = self.make_default_data()
    self.Liveries = {}

  def make_default_data(self):
    ld = {
      "config": {
        "ovgme": False
      },
      "liveries": {}
    }
    return ld

  def load_data(self):
    global DCSLMFolderName
    configPath = os.path.join(os.getcwd(), DCSLMFolderName, "dcslm.json")
    if os.path.isfile(configPath):
      try:
        with open(configPath, "r") as configFile:
          configData = json.load(configFile)
          return configData
      except:
        raise RuntimeError("Unable to open existing DCSLM config file at \'" + configPath + "\'")
    return None

  def write_data(self):
    global DCSLMFolderName
    configPath = os.path.join(os.getcwd(), DCSLMFolderName, "dcslm.json")
    print(configPath)
    try:
      with open(configPath, "w") as configFile:
        outJson = {}
        for k,v in self.LiveryData.items():
          outJson[k] = v
        json.dump(outJson, configFile)
    except:
      raise RuntimeError("Unable to write DCSLM config file to \'" + configPath + "\'")

  def make_dcslm_dir(self):
    global DCSLMFolderName
    dcslmPath = os.path.join(os.getcwd(), DCSLMFolderName)
    if not os.path.isdir(dcslmPath):
      try:
        os.mkdir(dcslmPath)
      except:
        raise RuntimeError("Unable to create DCSLM directory at \'" + dcslmPath + "\\\'")

  def get_registered_livery(self, id=None, livery=None):
    userID = id
    if livery:
      userID = livery.dcsuf.id
    if userID:
      if userID in self.LiveryData["liveries"].keys():
        return self.LiveryData["liveries"][userID]
    return None

  def is_livery_registered(self, id=None, livery=None):
    if self.get_registered_livery(id, livery):
      return True
    return False

  def register_livery(self, livery):
    if livery:
      if not self.is_livery_registered(livery.dcsuf.id):
        self.LiveryData["liveries"][livery.dcsuf.id] = livery.to_JSON()
        self.Liveries[livery.dcsuf.id] = livery
        return self.LiveryData["liveries"][livery.dcsuf.id]
    return None

  def unregister_livery(self, livery):
    if livery:
      if self.is_livery_registered(livery.dcsuf.id):
        del self.LiveryData["liveries"][livery.dcsuf.id]
        return True
    return False

  def load_livery_from_livery_registry_file(self, registryPath):
    if os.path.isfile(registryPath):
      try:
        with open(registryPath, "r") as registryFile:
          registryData = json.load(registryFile)
          loadedLivery = Livery.Livery()
          loadedLivery.from_JSON(registryData)
          return loadedLivery
      except:
        raise RuntimeError("Unable to open livery registry file at \'" + registryPath + "\'")
    else:
      raise RuntimeError("Unable to find livery registry file \'" + registryPath + "\'.")

  def write_livery_registry_file(self, livery):
    for i in livery.install:
      if self.LiveryData['config']['ovgme']:
        installRoot = os.path.join(os.getcwd(), "Liveries", livery.ovgme, i)
      else:
        installRoot = os.path.join(os.getcwd(), "Liveries", i)
      if os.path.isdir(installRoot):
        installPath = os.path.join(installRoot, ".dcslm")
        try:
          with open(installPath, "w") as registryFile:
            json.dump(livery.to_JSON(), registryFile)
        except:
          raise RuntimeError("Unable to write livery registry file to \'" + installPath + "\'.")
      else:
        raise RuntimeError("Unable to write livery registry file to \'" + installRoot + "\\\'. Was the livery folder created correctly?")

  def remove_livery_registry_file(self, livery):
    for i in livery['install']:
      if self.LiveryData['config']['ovgme']:
        installRoot = os.path.join(os.getcwd(), "Liveries", livery.ovgme, i)
      else:
        installRoot = os.path.join(os.getcwd(), "Liveries", i)
      installPath = os.path.join(installRoot, ".dcslm")
      if os.path.isfile(installPath):
        try:
          os.remove(installPath)
        except:
          raise RuntimeError("Unable to remove livery registry file at \'" + installPath + "\'.")
      else:
        raise RuntimeError("Unable to find livery registry file \'" + installPath + "\'.")

  def download_livery_archive(self, livery):
    if livery:
      return os.path.join(os.getcwd(), DCSLMFolderName, "archives", str.split(livery.dcsuf.download, '/')[-1])
    raise RuntimeError("Unable to get path for livery " + livery.title)

  def extract_livery_archive(self, livery):
    if livery:
      return True
    return False

  def detect_extracted_liveries(self, livery, extractPath):
    if livery:
      return [livery.title]
    return []

  def move_detected_liveries(self, livery, extractPath, detectedLiveries):
    if livery:
      return True
    return False

  def remove_extracted_livery_archive(self, livery, extractPath):
    if livery:
      return True
    return False

  def remove_downloaded_archive(self, livery, downloadPath):
    if livery:
      return True
    return False

  def generate_livery_destination_path(self, livery):
    if self.LiveryData['config']['ovgme']:
      return os.path.join(livery.ovgme, "Liveries")
    else:
      return "Liveries"

  def generate_aircraft_livery_install_path(self, livery, unitLiveries):
    liveryPaths = []
    destination = self.generate_livery_destination_path(livery)
    for unit in unitLiveries:
      liveryPaths.append(os.path.join(destination, unit))
    return liveryPaths

