import glob
import json
import os
import shutil
import re
import patoolib
import requests
from datetime import datetime
import DCSLM.Utilities as Utilities
from pprint import pprint
from .DCSUFParser import DCSUFParser
from .Livery import Livery
from .UnitManager import UM


class LiveryManager:
  def __init__(self):
    self.LiveryData = self.make_default_data()
    self.Liveries = {}
    self.FolderRoot = "DCSLM"
    self.console = None
    self.IDLocalMax = 3000000
    self.IDLocalLast = 1000000

  def print(self, *args, **kwargs):
    if self.console:
      self.console.print(*args, **kwargs)
    else:
      print(*args, **kwargs)

  def make_default_data(self):
    ld = {
      "config": {
        "ovgme": False
      },
      "liveries": {},
      "last_update": 0,
    }
    return ld

  def clear_data(self):
    self.LiveryData = self.make_default_data()
    self.Liveries = {}

  def load_data(self):
    configPath = os.path.join(os.getcwd(), self.FolderRoot, "dcslm.json")
    if os.path.isfile(configPath):
      try:
        with open(configPath, "r") as configFile:
          configData = json.load(configFile)
          for id,l in configData['liveries'].items():
            livery = Livery().from_JSON(l)
            self.Liveries[id] = livery
          return configData
      except:
        raise RuntimeError("Unable to open existing DCSLM config file at \'" + configPath + "\'")
    return None

  def write_data(self):
    configPath = os.path.join(os.getcwd(), self.FolderRoot, "dcslm.json")
    try:
      with open(configPath, "w") as configFile:
        outJson = {}
        for k,v in self.LiveryData.items():
          outJson[k] = v
        json.dump(outJson, configFile, indent=4)
        return outJson
    except:
      raise RuntimeError("Unable to write DCSLM config file to \'" + configPath + "\'")

  def make_dcslm_dirs(self):
    dcslmPath = os.path.join(os.getcwd(), self.FolderRoot)
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
      if str(userID) in self.Liveries.keys():
        return self.Liveries[str(userID)]
    return None

  def is_livery_registered(self, id=None, livery=None):
    if self.get_registered_livery(id, livery):
      return True
    return False

  def register_livery(self, livery):
    if livery:
      idStr = str(livery.dcsuf.id)
      self.LiveryData["liveries"][idStr] = livery.to_JSON()
      self.Liveries[idStr] = livery

  def _remove_installed_livery_directory(self, livery, installPath):
    if "Liveries" in installPath:
      if os.path.isdir(installPath) and Utilities.validate_remove_path(installPath):
        shutil.rmtree(installPath, ignore_errors=True)
      else:
        self.print("Warning: Livery uninstall path \'" + installPath + "\' is not a valid directory.", style="bold gold1")

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
        idStr = str(livery.dcsuf.id)
        if idStr in self.Liveries.keys():
          del self.Liveries[idStr]
        if idStr in self.LiveryData["liveries"].keys():
          del self.LiveryData["liveries"][idStr]
        return True
    return False

  def uninstall_livery(self, livery, keepFiles=False):
    if not keepFiles:
      self.remove_installed_livery_directories(livery)
    else:
      self.remove_livery_registry_files(livery)
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
              json.dump(livery.to_JSON(), registryFile, indent=4)
          except:
            raise RuntimeError("Unable to write livery registry file to \'" + installPath + "\'.")
        else:
          raise RuntimeError("Unable to write livery registry file to \'" + installRoot + "\\\'. Was the livery folder created correctly?")

  def remove_livery_registry_files(self, livery):
    for i, v in livery.installs['liveries'].items():
      for p in v['paths']:
        installRoot = os.path.join(os.getcwd(), livery.destination, p)
        if os.path.isdir(installRoot):
          registryPath = os.path.join(installRoot, ".dcslm.json")
          if os.path.isfile(registryPath) and Utilities.validate_remove_path(registryPath):
            try:
              Utilities.remove_file(registryPath)
            except:
              raise RuntimeError("Unable to remove livery registry file at \'" + registryPath + "\'.")
          else:
            raise RuntimeError("Unable to find livery registry file \'" + registryPath + "\'.")

  def download_livery_archive(self, livery, dlCallback=None, session=None, prependDCSUFID=True):
    if livery:
      if livery.dcsuf.download:
        archiveType = str.split(livery.dcsuf.download, '.')[-1]
        if archiveType in patoolib.ArchiveFormats:
          destinationPath = os.path.join(os.getcwd(), self.FolderRoot, "archives")
          archiveFilename = str.split(livery.dcsuf.download, '/')[-1]
          if prependDCSUFID:
            archiveFilename = str(livery.dcsuf.id) + "_" + archiveFilename
          destinationFilename = os.path.join(destinationPath, archiveFilename)
          try:
            if session:
              reqObj = session
            else:
              reqObj = requests
            with reqObj.get(livery.dcsuf.download, stream=True) as req:
              req.raise_for_status()
              with open(destinationFilename, 'wb') as f:
                if dlCallback:
                  dlCallback['progress'].start_task(dlCallback['task'])
                for chunk in req.iter_content(chunk_size=8192):
                  f.write(chunk)
                  if dlCallback:
                    dlCallback['exec'](dlCallback, len(chunk))
            return destinationFilename
          except (KeyboardInterrupt, IOError, ConnectionError, FileNotFoundError) as e:
            if os.path.isfile(destinationFilename):
              Utilities.remove_file(destinationFilename)
            raise RuntimeError("Failed during download of archive " + livery.dcsuf.download + ": " + str(e))
    raise RuntimeError("Unable to get downloaded archive path for livery \'" + livery.dcsuf.title + "\'.")

  def get_num_registered_liveries(self):
    return len(self.LiveryData['liveries'])

  def get_registered_livery_ids(self):
    return self.LiveryData['liveries'].keys()

  def get_size_registered_liveries(self):
    totalSize = 0
    for l in self.Liveries.values():
      liverySizeMB = Utilities.bytes_to_mb(l.get_size_installed_liveries())
      totalSize += liverySizeMB
    return totalSize

  def get_next_local_livery_id(self):
    validID = False
    localID = self.IDLocalLast + 1
    while not validID:
      if not self.get_registered_livery(localID):
        validID = True
      else:
        localID += 1
    if localID > self.IDLocalLast:
      self.IDLocalLast = localID
    return localID

  def download_screenshots(self, livery, session=None):
    DCSUFURLRoot = DCSUFParser().DCSDownloadUrlPrefix
    if livery.dcsuf.screenshots and len(livery.dcsuf.screenshots):
      # Check if able to create screenshot directory
      screenshotsPath = os.path.join(os.getcwd(), self.FolderRoot, "screenshots", str(livery.dcsuf.id))
      if not os.path.isdir(screenshotsPath):
        os.makedirs(screenshotsPath, exist_ok=True)
      downloadedFiles = []
      # Download every screenshot
      for s in livery.dcsuf.screenshots:
        downloadURL = DCSUFURLRoot + s
        splitURL = str.split(downloadURL, "/")
        imageFileName = splitURL[-1]
        downloadPath = os.path.join(screenshotsPath, imageFileName)
        downloadedFile = self._download_screenshot(downloadURL, downloadPath, session=session)
        if downloadedFile:
          downloadedFiles.append(downloadedFile)
          self.print("Downloaded screenshot \'" + imageFileName + "\'", style="")
        else:
          self.print("Failed to download screenshot \'" + imageFileName + "\'", style="bold red")
      return downloadedFiles
    return []

  def _download_screenshot(self, screenshotURL, screenshotPath, session=None):
    try:
      if session:
        reqObj = session
      else:
        reqObj = requests
      with reqObj.get(screenshotURL, stream=True) as req:
        req.raise_for_status()
        with open(screenshotPath, 'wb') as f:
          for chunk in req.iter_content(chunk_size=8192):
            f.write(chunk)
      return screenshotPath
    except (KeyboardInterrupt, IOError, ConnectionError, FileNotFoundError) as e:
      if os.path.isfile(screenshotPath):
        Utilities.remove_file(screenshotPath)
      raise RuntimeError("Failed during download of screenshot " + screenshotURL + ": " + str(e))

  def _remove_existing_extracted_files(self, livery, extractedRoot):
    if os.path.isdir(extractedRoot) and Utilities.validate_remove_path(extractedRoot):
      shutil.rmtree(extractedRoot, onerror=Utilities.remove_readonly)

  def extract_livery_archive(self, livery, verbose=False):
    if livery:
      if len(livery.archive):
        if os.path.isfile(livery.archive):
          extractRoot = os.path.join(os.getcwd(), self.FolderRoot, "extract", str(livery.dcsuf.id))
          archiveFolder = os.path.splitext(livery.archive)[0].split('\\')[-1]
          extractedPath = os.path.join(extractRoot, archiveFolder)
          extractedPath = (extractedPath + "\\").replace("\\", "/") # WinRAR doesn't like single backslashes
          if not os.path.isdir(extractedPath):
            os.makedirs(extractedPath, exist_ok=True)
          self._remove_existing_extracted_files(livery, extractedPath)
          self.extract_archive(livery, livery.archive, extractedPath, verbose=verbose, prefer7z=True)
          self._extract_extracted_archive(livery, extractedPath)
          return extractedPath
    return None

  def extract_archive(self, livery, archivePath, extractPath, verbose=False, prefer7z=True):
    prefProgram = None
    if patoolib.util.get_nt_7z_dir() != "" and prefer7z:
      prefProgram = "7z"
    patoolVerbosity = (2 if verbose else 0)
    patoolib.extract_archive(archivePath, patoolVerbosity, extractPath, program=prefProgram)

  def _extract_extracted_archive(self, livery, extractedPath):
    extractedFiles = glob.glob(extractedPath + "/**/*", recursive=True)
    for f in extractedFiles:
      if os.path.splitext(f)[-1][1:] in patoolib.ArchiveFormats:
        self.extract_archive(livery, f, extractedPath)

  def is_valid_livery_directory(self, fileList):
    for f in fileList:
      if "description.lua" in f:
        return True
    return False

  def is_valid_data_directory(self, fileList):
    for f in fileList:
      if ".dds" in f:
        return True
    return False

  def detect_extracted_liveries(self, livery, extractPath, extractedLiveryFiles):
    liveryDirectories = []
    for root, files in extractedLiveryFiles.items():
      liveryName = root
      folderData = {'name': liveryName, 'size': 0, 'data': False, 'root': False, 'path': root}
      if root != "\\":
        if not len(root): # Set livery name to DCSUF title if there is no folder root
          folderData['root'] = True
          liveryName = livery.dcsuf.title
        else: # Get livery name of last part of the path
          liveryName = str.split(root,"\\")[-1]
      if len(liveryName):
        folderData['name'] = liveryName
        folderData['size'] = self._get_size_of_extracted_livery_files(livery, extractPath, files)
        if not self.is_valid_livery_directory(files):
          if self.is_valid_data_directory(files):
            folderData['data'] = True
            folderData['name'] = root
          else:
            continue
        liveryDirectories.append(folderData)
    return liveryDirectories

  def does_archive_exist(self, archiveName):
    archiveFiles = glob.glob(os.path.join(os.getcwd(), self.FolderRoot, "archives") + "/*.*")
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

  def _get_size_of_extracted_livery_files(self, livery, extractPath, fileList):
    totalSize = 0
    for f in fileList:
      filePath = f
      if f[0] == "\\" or f[0] == "/":
        filePath = f[1:]
      extractedFilepath = os.path.join(extractPath, filePath)
      totalSize += os.path.getsize(extractedFilepath)
    return totalSize

  def _copy_livery_files(self, livery, extractPath, fileList, installLivery):
    badFiles = ['desktop.ini', 'thumbs.db']
    installDirectory = os.path.join(os.getcwd(), installLivery)
    if not os.path.isdir(installDirectory):
      os.makedirs(installDirectory, exist_ok=True)
    for f in fileList:
      splitPath = os.path.split(f)
      fileName = splitPath[1]
      if not '.' in fileName:
        continue
      badFileName = False
      for bF in badFiles:
        if bF in fileName:
          badFileName = True
          break
      if badFileName:
        continue
      filePath = f
      if f[0] == "\\" or f[0] == "/":
        filePath = f[1:]
      extractedFilepath = os.path.join(extractPath, filePath)
      destinationFilepath = os.path.join(installDirectory, fileName)
      shutil.copy2(extractedFilepath, destinationFilepath,)
    return True

  def copy_detected_liveries(self, livery, extractPath, extractedLiveryFiles, installPaths):
    copiedLiveries = []
    for install in installPaths:
      installPath = os.path.join(os.getcwd(), livery.destination, install)
      installLivery = str.split(installPath, "\\")[-1]
      for root, files in extractedLiveryFiles.items():
        rootUnit = livery.dcsuf.title
        if root != "\\":
          if not len(root):
            rootUnit = livery.dcsuf.title
          else:
            rootUnit = str.split(root, "\\")[-1]
        if installLivery == rootUnit:
          if self.is_valid_livery_directory(files) or self.is_valid_data_directory(files):
            if self._copy_livery_files(livery, extractPath, files, installPath):
              copiedLiveries.append(install)
              break
    return copiedLiveries

  def remove_extracted_livery_archive(self, livery, extractedID=None):
    if livery:
      folderID = livery.dcsuf.id
      if extractedID:
        folderID = extractedID
      extractRoot = os.path.join(os.getcwd(), self.FolderRoot, "extract", str(folderID))
      if os.path.exists(extractRoot):
        if Utilities.validate_remove_path(extractRoot):
          shutil.rmtree(extractRoot, onerror=Utilities.remove_readonly)
          return True
        else:
          raise RuntimeError("Invalid path provided to remove extracted livery archive: " + extractRoot)
    return False

  def remove_downloaded_archive(self, livery, downloadPath):
    if livery:
      archivePath = os.path.join(os.getcwd(), self.FolderRoot, "archives", livery.archive)
      if os.path.isfile(archivePath):
        Utilities.remove_file(archivePath)
        return True
      else:
        raise RuntimeWarning("Unable to remove archive file \'" + archivePath + "\' as it doesn't exist.")
    return False

  def generate_livery_destination_path(self, livery):
    if self.LiveryData['config']['ovgme']:
      return os.path.join(livery.ovgme, "Liveries")
    else:
      return "Liveries"

  def generate_livery_install_paths(self, livery, detectedUnits, detectedLiveries):
    installPaths = []
    for dU in detectedUnits:
      livery.installs['liveries'][dU['name']] = {'size': 0, 'paths': [], 'data': 0}
      for dL in detectedLiveries:
        if dL['name'] == dU['name']:
          for l in dU['liveries']:
            lPath = os.path.join(l, dU['name'])
            installPaths.append(lPath)
            livery.installs['liveries'][dU['name']]['paths'].append(lPath)
          break
    return installPaths

  def get_livery_data_from_dcsuf_url(self, url, session=None):
    if len(url):
      l = Livery()
      l.dcsuf = DCSUFParser().get_dcsuserfile_from_url(url, session)
      return l
    raise RuntimeError("Unable to get livery data from url \'" + url + "\'")

  def get_livery_data_from_archive(self, path, id):
    if len(path) and os.path.isfile(path):
      l = Livery()
      l.dcsuf.id = id
      l.dcsuf.size = Utilities.bytes_to_mb_string(os.path.getsize(path)) + " Mb"
      l.dcsuf.datetime = datetime.fromtimestamp(os.path.getmtime("{}".format(path)))
      l.dcsuf.date = l.dcsuf.datetime_to_date(l.dcsuf.datetime)
      l.dcsuf.download = path
      l.dcsuf.author = "Unknown"
      l.dcsuf.tags = []
      archiveFile = os.path.split(path)[1]
      archiveName = os.path.splitext(archiveFile)[0]
      l.dcsuf.title = archiveName
      return l
    raise RuntimeError("Unable to get livery data from path \'" + path + "\'")

  def request_archive_size(self, archiveURL):
    if len(archiveURL):
      return Utilities.request_file_size(archiveURL)
    return 0

  def _count_unit_parts(self, descParts):
    unitPartsCount = {}
    for p in descParts:
      for c in UM.Categories:
        if c in UM.Units.keys():
          for u, d in UM.Units[c].items():
            unitCount = 0
            for uP in d.parts:
              if uP == p:
                unitCount += 1
            if unitCount > 0:
              if not d in unitPartsCount:
                unitPartsCount[d] = unitCount
              else:
                unitPartsCount[d] += unitCount
    return unitPartsCount

  def determine_unit_from_description_path(self, descPath, dlPath):
    splitDLPath = os.path.split(dlPath)
    dlPathUnit = None
    if len(splitDLPath) > 1:
      dlPathUnit = UM.get_unit_from_liveries_dir(splitDLPath[-2])
    if dlPathUnit:
      return dlPathUnit
    descLines = self._optimize_get_desclines_from_description_file(descPath)
    descParts = self._get_parts_from_description(descLines)
    unitPartsCount = self._count_unit_parts(descParts)
    if len(unitPartsCount.keys()) > 0:
      return max(unitPartsCount, key=unitPartsCount.get)
    else:
      return None

  def _get_file_lines(self, filePath):
    if os.path.isfile(filePath):
      with open(filePath, "r", errors="ignore") as readFile:
        return readFile.readlines()
    return []

  def _optimize_get_lua_statements_from_line(self, line, commentStart=None, commentEnd=None):
    if not commentStart:
      commentStart = len(line) + 1
    if not commentEnd:
      commentEnd = -1
    luaStatements = []
    reStatement = re.findall("(.+[;\n])", line)
    if len(reStatement):
      for rs in reStatement:
        luaStatement = str.strip(rs)
        splitStatements = str.split(luaStatement, ';')
        for s in splitStatements:
          s = s[str.find(s, '{'):str.find(s, '}') + 1]
          subStrStart = str.find(line, s)
          if not (subStrStart > commentStart and subStrStart < commentEnd - 2) and len(s):
            luaStatements.append(s)
    return luaStatements

  def _optimize_get_py_statements_from_line(self, line, commentStart=None, commentEnd=None):
    luaStatements = self._optimize_get_lua_statements_from_line(line, commentStart, commentEnd)
    pyStatements = []
    for ls in luaStatements:
      ps = self._optimize_lua_statement_to_py(ls)
      if len(ps) == 4:
        pyStatements.append(ps)
    return pyStatements

  def _optimize_py_statement_to_lua(self, pyStatement, rootLivery = "", rootLiveryPath = "") -> str:
    if len(pyStatement) == 4:
      if pyStatement[2].startswith("../"):
        splitExistingPath = str.split(pyStatement[2], '/')
        detectedRootLivery = splitExistingPath[-2] + "/"
        if detectedRootLivery != rootLivery and rootLivery:
          rootLivery = detectedRootLivery
          pyStatement[2] = splitExistingPath[-1]
      correctedPath = rootLiveryPath + rootLivery + pyStatement[2]
      luaStatement = "{\"" + pyStatement[0] + "\", " + pyStatement[1] + " ,\"" + correctedPath + "\","
      if pyStatement[3]:
        luaStatement += "true"
      else:
        luaStatement += "false"
      luaStatement = luaStatement + "}"
      return luaStatement
    return ""

  def _optimize_lua_statement_to_py(self, luaStatement):
    luaData = []
    splitStatement = str.split(luaStatement[1:-1], ',')
    if len(splitStatement) == 4:
      splitStatement[0] = re.search("\".+\"", str.strip(splitStatement[0])).group()[1:-1]
      splitStatement[1] = str.strip(str.strip(splitStatement[1]))
      splitStatement[2] = re.search("\".+\"", str.strip(splitStatement[2])).group()[1:-1]
      if splitStatement[2].startswith('..'):
        splitStatement[2] = os.path.normpath(splitStatement[2]).replace('\\', '/')
      splitStatement[3] = False if (str.lower(str.strip(splitStatement[3])) == "false") else True
      luaData = splitStatement
    return luaData

  def _get_py_statements_from_description(self, descLines):
    inCommentBlock = False
    pyStatements = []
    for line in descLines:
      commentStart = str.find(line, "--")
      blockStart = str.find(line, "--[[")
      if blockStart != -1:
        blockStart -= 2
        inCommentBlock = True
      blockEnd = str.find(line, "]]")
      if blockEnd > -1:
        commentStart = str.find(line, "--", blockEnd - 2)
        inCommentBlock = False
      if commentStart < 0:
        commentStart = len(line) + 1
      if not inCommentBlock:
        pyStatements.extend(self._optimize_get_py_statements_from_line(line, commentStart, blockEnd))
    return pyStatements

  def _get_parts_from_description(self, descLines):
    parts = []
    pyStatements = self._get_py_statements_from_description(descLines)
    for ps in pyStatements:
      lowerPart = str.lower(ps[0])
      if not lowerPart in parts:
        parts.append(lowerPart)
    return parts

  def _get_file_refs_from_description(self, descLines):
    fileRefs = {}
    pyStatements = self._get_py_statements_from_description(descLines)
    for ps in pyStatements:
      if not ps[3]:
        partStr = ps[0] + ':' + ps[1]
        if not ps[2] in fileRefs.keys():
          fileRefs[ps[2]] = {'parts': []}
        if not partStr in fileRefs[ps[2]]['parts']:
          fileRefs[ps[2]]['parts'].append(partStr)
    return fileRefs

  def _get_file_list_data_folder(self, livery, liveryData):
    dataFiles = {}
    if liveryData:
      installRoot = os.path.join(os.getcwd(), livery.destination, liveryData['paths'][0])
      liveryFiles = glob.glob(installRoot + "\\*.*")
      for path in liveryFiles:
        splitPath = str.split(path, '\\')
        splitF = str.split(splitPath[-1], '.')
        fileName = splitF[0]
        dataFiles[fileName] = {'parts': []}
    return dataFiles

  def _optimize_generate_file_hashes(self, installRoot, liveryTitle, fileRefs):
    fileHashes = {}
    for f, d in fileRefs.items():
      filepath = os.path.abspath(os.path.join(installRoot, f))
      splitFile = str.split(filepath, '\\')
      if not "." in splitFile[-1]:
        detectedFormat = Utilities.find_desc_file_format(filepath)
        filepath += "." + detectedFormat
      if os.path.isfile(filepath):
        fileHash = Utilities.hash_file(filepath)
        if fileHash:
          d['hash'] = fileHash
          if not fileHash in fileHashes.keys():
            fileHashes[fileHash] = [liveryTitle]
          else:
            if liveryTitle not in fileHashes[fileHash]:
              fileHashes[fileHash].append(liveryTitle)
      else:
        self.print("Unable to hash missing file " + filepath, style="bold red")
    return fileHashes

  def _optimize_find_unused_livery_files(self, livery, liveryFilesData):
    skipFiles = ["description.lua", "orig_description.lua", ".dcslm"]
    unusedFiles = []
    liveryFiles = {}
    for l,lfd in liveryFilesData.items():
      liveryFiles[l] = []
      for lf,d in lfd.items():
        if len(d['parts']):
          liveryFiles[l].append(str.lower(lf))
    for t, l in livery.installs['liveries'].items():
      destRoot = os.path.join(os.getcwd(), livery.destination)
      installRoot = os.path.join(destRoot, l['paths'][0])
      installedFiles = glob.glob(installRoot + "\\*.*")
      for iF in installedFiles:
        splitPath = str.split(iF, "\\")
        livIndex = splitPath.index("Liveries")
        if splitPath[-1] in skipFiles:
          continue
        splitLivery = '\\'.join(splitPath[livIndex+2:-1])
        shortName = os.path.splitext(splitPath[-1])[0]
        lowerName = str.lower(shortName)
        if splitLivery in liveryFiles.keys():
          if lowerName not in liveryFiles[splitLivery] and lowerName + ".dds" not in liveryFiles[splitLivery]:
            unusedFiles.append(os.path.join(livery.destination, l['paths'][0], splitPath[-1]))
      if len(l['paths']) > 1:
        for u in l['paths'][1:]:
          additionalInstallRoot = os.path.join(destRoot, u)
          additionalFiles = glob.glob(additionalInstallRoot + "\\*.*")
          for aiF in additionalFiles:
            splitPath = str.split(aiF, "\\")
            if splitPath[-1] in skipFiles:
              continue
            unusedFiles.append(os.path.join(livery.destination, u, splitPath[-1]))
    return unusedFiles

  def _optimize_correct_desc_lines(self, filesData, descLines, units, commentLine=False):
    optimizedLines = {}
    for t in descLines.keys():
      optimizedLines[t] = {}
      for dL in descLines[t]:
        optimizedLines[t][dL] = []
    #rootUnit = units[0]
    #rootLiveryPath = "../../" + rootUnit + "/"
    rootLiveryPath = "nah"
    for t, dL in descLines.items():
      if not len(dL):
        continue
      rootLivery = t + '/'
      for lU in dL.keys():
        for line in dL[lU]:
          if line[:2] == '--':
            optimizedLines[t][lU].append(line)
            continue
          pyStatements = self._optimize_get_py_statements_from_line(line)
          optimizeStatement = False
          for ps in pyStatements:
            for l, fd in filesData['liveries'].items():
              if ps[2] in fd.keys():
                matchedData = fd[ps[2]]
                if not 'hash' in matchedData.keys():
                  continue
                if matchedData['hash'] in filesData['hashes'].keys():
                  matchedHash = filesData['hashes'][matchedData['hash']]
                  if t not in matchedHash:
                    continue
                  if len(matchedHash) > 1:
                    replacementTitle = matchedHash[0]
                    fileStr = str.split(ps[2], "/")[-1]
                    if replacementTitle == t:
                      replacementPath = fileStr
                    else:
                      replacementPath = "../" + replacementTitle + "/" + fileStr
                    ps[2] = replacementPath
                    optimizeStatement = True
                if len(units) > 1:
                  optimizeStatement = True
          if not optimizeStatement:
            optimizedLines[t][lU].append(line)
          else:
            if commentLine:
              optimizedLines[t][lU].append("--" + line)
            linePrefix = str.find(line, '{')
            lastBracket = str.rfind(line, '}')
            correctedLuaStatements = []
            for ps in pyStatements:
              ls = self._optimize_py_statement_to_lua(ps)
              if len(ls):
                correctedLuaStatements.append(ls)
            correctedLuaLine = line[:linePrefix] + ' '.join(correctedLuaStatements) + line[lastBracket + 1:]
            optimizedLines[t][lU].append(correctedLuaLine)
    return optimizedLines

  def _optimize_write_corrected_desc_files(self, livery, descLines, keepCopy=True):
    for t in descLines.keys():
      for l, lines in descLines[t].items():
        descRoot = os.path.join(os.getcwd(), livery.destination, l, t)
        descPath = os.path.join(descRoot, "description.lua")
        if os.path.isfile(descPath):
          if keepCopy:
            shutil.move(descPath, os.path.join(descRoot, "orig_description.lua"))
          with open(descPath, "w") as descFile:
            self.print("Writing \'" + descPath + "\'", style="bold green")
            descFile.writelines(lines)

  def _optimize_remove_unused_files(self, unusedData):
    for f in unusedData:
      fPath = os.path.join(os.getcwd(), f)
      Utilities.remove_file(fPath)

  def _optimize_get_desclines_from_description_file(self, descPath):
    descLines = []
    if os.path.isfile(descPath):
      descLines = self._get_file_lines(descPath)
    return descLines

  def _optimize_get_desclines_from_livery(self, livery):
    descLines = {}
    for t, l in livery.installs['liveries'].items():
      descLines[t] = {}
      for p in l['paths']:
        installRoot = os.path.join(os.getcwd(), livery.destination, p)
        descPath = os.path.join(installRoot, "description.lua")
        if 'data' not in l.keys():
          l['data'] = False
        if not l['data']:
          descLines[t][p] = self._optimize_get_desclines_from_description_file(descPath)
        else:
          descLines[t][p] = []
    return descLines

  def _optimize_get_filerefs_from_desclines(self, livery, descLines):
    filesData = {}
    for t, l in livery.installs['liveries'].items():
      if t in descLines.keys():
        for p in descLines[t]:
          if 'data' not in l.keys() or not l['data']:
            fileRefs = self._get_file_refs_from_description(descLines[t][p])
            filesData[p] = fileRefs
          else:
            filesList = self._get_file_list_data_folder(livery, l)
            filesData[p] = filesList
    # Consolidate relative file paths with other liveries
    for p in filesData.keys():
      movedFiles = []
      for f in filesData[p].keys():
        if f.startswith("../"):
          splitFile = f.split("/")
          splitLivery = '\\'.join(splitFile[1:-1])
          if splitLivery in filesData.keys():
            for part in filesData[p][f]['parts']:
              if splitFile[-1] in filesData[splitLivery].keys():
                if part not in filesData[splitLivery][splitFile[-1]]['parts']:
                  filesData[splitLivery][splitFile[-1]]['parts'].append(part)
            movedFiles.append(f)
      for mF in movedFiles:
        del filesData[p][mF]
    return filesData

  def _optimize_calculate_fileref_hashes(self, livery, fileRefs):
    filesData = {}
    for t, l in livery.installs['liveries'].items():
      self.print("Generating file hashes for \'" + t + "\'", style="bold gold1")
      for p in l['paths']:
        installRoot = os.path.join(os.getcwd(), livery.destination, p)
        if p in fileRefs.keys():
          fileHashes = self._optimize_generate_file_hashes(installRoot, t, fileRefs[p])
          for fh, lf in fileHashes.items():
            if fh not in filesData.keys():
              filesData[fh] = lf
            else:
              filesData[fh].extend(lf)
    return filesData

  def _optimize_find_missing_files(self, liveryFileHashes, liveryFilesData):
    missingFiles = {}
    for t in liveryFilesData.keys():
      for f in liveryFilesData[t].keys():
        if 'hash' not in liveryFilesData[t][f].keys():
          if t not in missingFiles:
            missingFiles[t] = []
          missingFiles[t].append(f + ".dds")
    return missingFiles

  def optimize_livery(self, livery, removeUnused=False, copyDesc=False, verbose=False, checkOnly=False):
    if livery:
      filesData = {'liveries': {}, 'hashes': {}, 'same_hash':[], 'size': {} }
      descLines = self._optimize_get_desclines_from_livery(livery)
      filesData['liveries'] = self._optimize_get_filerefs_from_desclines(livery, descLines)
      filesData['hashes'] = self._optimize_calculate_fileref_hashes(livery, filesData['liveries'])
      filesData['same_hash'] = [h for h,l in filesData['hashes'].items() if len(l) > 1]
      if len(filesData['same_hash']):
        self.print("Matched " + str(len(filesData['same_hash'])) + " files with the same hash.")
      filesData['unused'] = self._optimize_find_unused_livery_files(livery, filesData['liveries'])
      if len(filesData['unused']):
        self.print("Found " + str(len(filesData['unused'])) + " unused files.")
      filesData['missing'] = self._optimize_find_missing_files(filesData['hashes'], filesData['liveries'])
      if len(filesData['missing']):
        self.print("Detected " + str(len(filesData['missing'])) + " missing files.")
      livery.calculate_size_installed_liveries()
      filesData['size']['before'] = livery.get_size_installed_liveries()
      if (len(filesData['same_hash']) or len(livery.installs['units']) > 1) and not checkOnly:
        correctedLines = self._optimize_correct_desc_lines(filesData, descLines, livery.installs['units'])
        self._optimize_write_corrected_desc_files(livery, correctedLines, keepCopy=copyDesc)
      if removeUnused or checkOnly:
        newDescLines = self._optimize_get_desclines_from_livery(livery)
        filesData['new_liveries'] = self._optimize_get_filerefs_from_desclines(livery, newDescLines)
        filesData['unused'] = self._optimize_find_unused_livery_files(livery, filesData['new_liveries'])
        if len(filesData['unused']):
          if verbose:
            if not checkOnly:
              self.print("Removing the following unused files:")
            else:
              self.print("Found the following unused files:")
            shortUnused = []
            for u in filesData['unused']:
              shortUnused.append('\\'.join(str.split(u, "\\")[-2:]))
            self.print(shortUnused)
          else:
            if not checkOnly:
              self.print("Removing " + str(len(filesData['unused'])) + " unused files.")
            else:
              self.print("Found " + str(len(filesData['unused'])) + " unused files.")
        if not checkOnly:
          self._optimize_remove_unused_files(filesData['unused'])
          livery.calculate_size_installed_liveries()
      filesData['size']['after'] = livery.get_size_installed_liveries()
      return filesData
    return None
