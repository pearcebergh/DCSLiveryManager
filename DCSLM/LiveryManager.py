from .Livery import Livery
from .UnitConfig import Units
from .DCSUFParser import DCSUFParser, ArchiveExtensions
import DCSLM.Utilities as Utilities
import os, sys
import json
import glob
import shutil
import patoolib
from patoolib.programs import *
import requests

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
          for id,l in configData['liveries'].items():
            self.Liveries[id] = Livery().from_JSON(l)
          return configData
      except:
        raise RuntimeError("Unable to open existing DCSLM config file at \'" + configPath + "\'")
    return None

  def write_data(self):
    global DCSLMFolderName
    configPath = os.path.join(os.getcwd(), DCSLMFolderName, "dcslm.json")
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

  def get_registered_livery(self, id=None, livery=None, title=None):
    # TODO: Search by title
    userID = id
    if livery:
      userID = livery.dcsuf.id
    if userID:
      if str(userID) in self.Liveries.keys():
        return self.Liveries[str(userID)]
    return None

  def is_livery_registered(self, id=None, livery=None):
    if self.get_registered_livery(id, livery):
      return True
    return False

  def register_livery(self, livery):
    if livery:
      #if not self.is_livery_registered(livery.dcsuf.id):
      self.LiveryData["liveries"][str(livery.dcsuf.id)] = livery.to_JSON()
      self.Liveries[str(livery.dcsuf.id)] = livery

  def _remove_installed_livery_directory(self, livery, installPath):
    if "Liveries" in installPath:
      if os.path.isdir(installPath):
        shutil.rmtree(installPath, ignore_errors=True)
      else:
        raise RuntimeError("Install path \'" + installPath + "\' is not a valid directory.")

  def remove_installed_livery_directories(self, livery):
    for i in livery.installs['liveries'].values():
      for p in i['paths']:
        fullPath = os.path.join(os.getcwd(), livery.destination, p)
        self._remove_installed_livery_directory(livery, fullPath)
    livery.installs['liveries'] = {}
    return None

  def unregister_livery(self, livery):
    if livery:
      if self.is_livery_registered(livery.dcsuf.id):
        del self.Liveries[str(livery.dcsuf.id)]
        del self.LiveryData["liveries"][str(livery.dcsuf.id)]
        return True
    return False

  def uninstall_livery(self, livery):
    self.remove_installed_livery_directories(livery)
    self.unregister_livery(livery)

  def load_livery_from_livery_registry_file(self, registryPath):
    if os.path.isfile(registryPath):
      try:
        with open(registryPath, "r") as registryFile:
          registryData = json.load(registryFile)
          loadedLivery = Livery()
          loadedLivery.from_JSON(registryData)
          return loadedLivery
      except:
        raise RuntimeError("Unable to open livery registry file at \'" + registryPath + "\'")
    else:
      raise RuntimeError("Unable to find livery registry file \'" + registryPath + "\'.")

  def write_livery_registry_files(self, livery):
    for i, v in livery.installs['liveries'].items():
      for p in v['paths']:
        installRoot = os.path.join(os.getcwd(), livery.destination, p)
        if os.path.isdir(installRoot):
          installPath = os.path.join(installRoot, ".dcslm.json")
          try:
            with open(installPath, "w") as registryFile:
              json.dump(livery.to_JSON(), registryFile)
          except:
            raise RuntimeError("Unable to write livery registry file to \'" + installPath + "\'.")
        else:
          raise RuntimeError("Unable to write livery registry file to \'" + installRoot + "\\\'. Was the livery folder created correctly?")

  def remove_livery_registry_files(self, livery):
    for i, v in livery.installs['liveries'].items():
      for p in v['paths']:
        installRoot = os.path.join(os.getcwd(), livery.destination, p)
        if os.path.isdir(installRoot):
          installPath = os.path.join(installRoot, ".dcslm.json")
          if os.path.isfile(installPath):
            try:
              os.remove(installPath)
            except:
              raise RuntimeError("Unable to remove livery registry file at \'" + installPath + "\'.")
          else:
            raise RuntimeError("Unable to find livery registry file \'" + installPath + "\'.")

  def download_livery_archive(self, livery, dlCallback=None):
    # TODO: Make archive path relative
    if livery:
      if livery.dcsuf.download:
        archiveType = '.' + str.split(livery.dcsuf.download, '.')[-1]
        if archiveType in ArchiveExtensions:
          destinationPath = os.path.join(os.getcwd(), DCSLMFolderName, "archives")
          archiveFilename = str.split(livery.dcsuf.download, '/')[-1]
          destinationFilename = os.path.join(destinationPath, archiveFilename)
          with requests.get(livery.dcsuf.download, stream=True) as req:
            req.raise_for_status()
            with open(destinationFilename, 'wb') as f:
              if dlCallback:
                dlCallback['progress'].start_task(dlCallback['task'])
              for chunk in req.iter_content(chunk_size=8192):
                f.write(chunk)
                if dlCallback:
                  dlCallback['exec'](livery, dlCallback, len(chunk))
          return destinationFilename
    raise RuntimeError("Unable to get downloaded archive path for livery \'" + livery.dcsuf.title + "\'.")

  def _remove_existing_extracted_files(self, livery, extractedRoot):
    if os.path.isdir(extractedRoot):
      shutil.rmtree(extractedRoot)

  def extract_livery_archive(self, livery):
    if livery:
      if len(livery.archive):
        archivePath = os.path.join(os.getcwd(), DCSLMFolderName, "archives", livery.archive)
        if os.path.isfile(archivePath):
          extractRoot = os.path.join(os.getcwd(), DCSLMFolderName, "extract", str(livery.dcsuf.id))
          if not os.path.isdir(extractRoot):
            os.makedirs(extractRoot, exist_ok=True)
          archiveFile = livery.archive
          archiveFolder = os.path.splitext(archiveFile)[0].split('\\')[-1]
          extractedPath = os.path.join(extractRoot, archiveFolder)
          self._remove_existing_extracted_files(livery, extractedPath)
          patoolib.extract_archive(archivePath, 0, extractedPath)
          return extractedPath
    return None

  def is_valid_livery_directory(self, fileList):
    for f in fileList:
      if "description.lua" in f:
        return True
    return False

  def detect_extracted_liveries(self, livery, extractPath, extractedLiveryFiles):
    liveryDirectories = []
    for root, files in extractedLiveryFiles.items():
      liveryName = root
      if root != "\\":
        liveryName = str.split(root,"\\")[-1]
      if len(liveryName):
        if self.is_valid_livery_directory(files):
          liverySize = self.get_size_of_livery_files(livery, extractPath, files)
          liveryDirectories.append({'name': liveryName, 'size': liverySize})
          #liveryDirectories.append(liveryName)
    return liveryDirectories

  def does_archive_exist(self, archiveName):
    archiveFiles = glob.glob(os.path.join(os.getcwd(), DCSLMFolderName, "archives") + "/*.*")
    for a in archiveFiles:
      if archiveName in a:
        return a
    return None

  def compare_archive_sizes(self, archivePath, archiveURL):
    if os.path.isfile(archivePath):
      fileSize = os.path.getsize(archivePath)
      urlSize = self.request_archive_size(archiveURL)
      return fileSize == urlSize
    return False

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

  def get_size_of_livery_files(self, livery, extractPath, fileList):
    totalSize = 0
    for f in fileList:
      extractedFilepath = os.path.join(extractPath, f[1:])
      totalSize += os.path.getsize(extractedFilepath)
    return totalSize

  def _copy_livery_files(self, livery, extractPath, fileList, installLivery):
    badFiles = ['desktop.ini', 'thumbs.db']
    installDirectory = os.path.join(os.getcwd(), installLivery)
    if not os.path.isdir(installDirectory):
      os.makedirs(installDirectory, exist_ok=True)
    for f in fileList:
      fileName = os.path.split(f)[1]
      badFileName = False
      for bF in badFiles:
        if bF in fileName:
          badFileName = True
          break
      if badFileName:
        continue
      extractedFilepath = os.path.join(extractPath, f[1:])
      destinationFilepath = os.path.join(installDirectory, fileName)
      shutil.copy2(extractedFilepath, destinationFilepath,)
    return True

  def copy_detected_liveries(self, livery, extractPath, extractedLiveryFiles, installPaths):
    # TODO: Fix copying directories within valid livery dirs (3300601, 3315181)
    copiedLiveries = []
    for install in installPaths:
      installPath = os.path.join(os.getcwd(), livery.destination, install)
      installLivery = str.split(installPath, "\\")[-1]
      for root, files in extractedLiveryFiles.items():
        if self.is_valid_livery_directory(files):
          rootLivery = livery.dcsuf.title
          if root != "\\":
            rootLivery = str.split(root, "\\")[-1]
          if installLivery == rootLivery:
            if self._copy_livery_files(livery, extractPath, files, installPath):
              copiedLiveries.append(install)
    return copiedLiveries

  def remove_extracted_livery_archive(self, livery):
    if livery:
      extractRoot = os.path.join(os.getcwd(), DCSLMFolderName, "extract", str(livery.dcsuf.id))
      shutil.rmtree(extractRoot, ignore_errors=True)
      return True
    return False

  def remove_downloaded_archive(self, livery, downloadPath):
    if livery:
      archivePath = os.path.join(os.getcwd(), DCSLMFolderName, "archives", livery.archive)
      if os.path.isfile(archivePath):
        #os.remove(archivePath)
        return True
      else:
        raise RuntimeWarning("Unable to remove archive file \'" + archivePath + "\' as it doesn't exist.")
    return False

  def generate_livery_destination_path(self, livery):
    if self.LiveryData['config']['ovgme']:
      return os.path.join(livery.ovgme, "Liveries")
    else:
      return "Liveries"

  def generate_aircraft_livery_install_path(self, livery, unitLiveries):
    liveryPaths = []
    for unit in unitLiveries:
      liveryPaths.append(os.path.join(unit))
    return liveryPaths

  def generate_livery_install_paths(self, livery, installRoots, detectedLiveries):
    installPaths = []
    for dl in detectedLiveries:
      if dl['name'] == "\\":
        dl['name'] = livery.dcsuf.title
      livery.installs['liveries'][dl['name']] = {'size': dl['size'], 'paths':[]}
      for root in installRoots:
        livery.installs['liveries'][dl['name']]['paths'].append(os.path.join(root, dl['name']))
        installPaths.append(os.path.join(root, dl['name']))
    return installPaths

  def get_livery_data_from_dcsuf_url(self, url):
    if len(url):
      l = Livery()
      l.dcsuf = DCSUFParser().get_dcsuserfile_from_url(url)
      l.ovgme = l.generate_ovgme_folder()
      return l
    raise RuntimeError("Unable to get livey data from url " + url)

  def request_archive_size(self, livery):
    if livery.dcsuf.archive:
      return Utilities.request_file_size(livery.dcsuf.archive)
    return 0
