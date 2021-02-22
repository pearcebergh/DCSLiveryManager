from . import Livery
from .UnitConfig import Units
import os, sys
import json
import glob
import shutil

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

  def make_dcslm_dirs(self):
    global DCSLMFolderName
    dcslmPath = os.path.join(os.getcwd(), DCSLMFolderName)
    archivesPath = os.path.join(dcslmPath, "archives")
    extractPath = os.path.join(dcslmPath, "extract")
    try:
      if not os.path.isdir(dcslmPath):
        os.mkdir(dcslmPath)
      if not os.path.isdir(archivesPath):
        os.mkdir(archivesPath)
      if not os.path.isdir(extractPath):
        os.mkdir(extractPath)
    except:
      raise RuntimeError("Unable to create DCSLM directories at \'" + dcslmPath + "\\\'")

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

  def write_livery_registry_files(self, livery):
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
      # do the extract
      return os.path.join(os.getcwd(), DCSLMFolderName, "extract", str(livery.dcsuf.id))
    return None

  def is_valid_livery_directory(self, fileList):
    for f in fileList:
      if "description.lua" in f:
        return True
    return False

  def detect_extracted_liveries(self, livery, extractedLiveryFiles):
    liveryDirectories = []
    for root, files in extractedLiveryFiles.items():
      liveryName = str.split(root,"\\")[-1]
      if len(liveryName):
        if self.is_valid_livery_directory(files):
          liveryDirectories.append(liveryName)
    return liveryDirectories

  def get_extracted_livery_files(self, livery, extractPath):
    extractedFiles = glob.glob(extractPath + "/**/*", recursive=True)
    for i in range(0, len(extractedFiles)): # Remove extract root from glob filenames
      extractedFiles[i] = extractedFiles[i][len(extractPath):]
    if livery:
      directoryFiles = {}
      for f in extractedFiles:
        splitF = os.path.split(f)
        if splitF[0] not in directoryFiles:
          directoryFiles[splitF[0]] = []
        directoryFiles[splitF[0]].append(f)
      return directoryFiles
    return None

  def _copy_livery_files(self, livery, extractPath, fileList, installLivery):
    installDirectory = os.path.join(os.getcwd(), installLivery)
    if not os.path.isdir(installDirectory):
      os.makedirs(installDirectory, exist_ok=True)
    for f in fileList:
      fileName = os.path.split(f)[1]
      extractedFilepath = os.path.join(extractPath, f[1:])
      destinationFilepath = os.path.join(installDirectory, fileName)
      shutil.copy(extractedFilepath, destinationFilepath)
    return True

  def copy_detected_liveries(self, livery, extractPath, extractedLiveryFiles, detectedLiveries, installPaths):
    copiedLiveries = []
    for install in installPaths:
      installLivery = str.split(install, "\\")[-1]
      for root, files in extractedLiveryFiles.items():
        rootLivery = str.split(root, "\\")[-1]
        if installLivery == rootLivery:
          if self._copy_livery_files(livery, extractPath, files, install):
            copiedLiveries.append(install)
    return copiedLiveries

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
    for unit in unitLiveries:
      liveryPaths.append(os.path.join(livery.destination, unit))
    return liveryPaths

  def generate_livery_install_paths(self, installRoots, detectedLiveries):
    installPaths = []
    for root in installRoots:
      for livery in detectedLiveries:
        installPaths.append(os.path.join(root, livery))
    return installPaths
