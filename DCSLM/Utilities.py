import re
import os
import stat
import hashlib
import glob
import shutil
from requests import get

def find_desc_file_format(knownFilePath):
  detectedFormat = "dds"
  matchedFiles = glob.glob(knownFilePath + ".*")
  if len(matchedFiles):
    detectedFormat = matchedFiles[0].split(".")[-1]
  return detectedFormat

def hash_file(filePath):
  if os.path.isfile(filePath):
    with open(filePath, "rb") as hashFile:
      hashData = hashFile.read()
      fileHash = hashlib.md5(hashData).hexdigest()
      return fileHash
  return None

def correct_dcs_user_files_url(fileURL):
  DCSFilesURLRoot = "https://www.digitalcombatsimulator.com/en/files/"
  fileID = re.findall(r'[0-9]+', fileURL)
  if len(fileID):
    if str.isnumeric(fileID[0]):
      return DCSFilesURLRoot + fileID[0] + "/", fileID[0]
  return "", 0

def bytes_to_mb(sizeBytes):
  return float(sizeBytes/(10**6))

def bytes_to_mb_string(sizeBytes):
  return "{:.2f}".format(float(sizeBytes/(10**6)))

def mb_to_mb_string(sizeMegabytes):
  return "{:.2f}".format(sizeMegabytes)

def mb_to_gb_string(sizeMegabytes):
  return "{:.2f}".format(sizeMegabytes/(10**3))

def request_file_size(fileURL):
  return int(get(fileURL, stream=True).headers['Content-length'])

def validate_remove_path(filepath):
  if len(filepath):
    if os.getcwd() in os.path.normpath(filepath):
      return True
  return False

def remove_file(filepath):
  if validate_remove_path(filepath):
    os.remove(filepath)
    return
  raise RuntimeWarning("Tried to remove file not in path of DCSLM! " + str(filepath))

def remove_files(fileList):
  for f in fileList:
    remove_file(f)

def remove_directory(dirPath):
  if validate_remove_path(dirPath):
    shutil.rmtree(dirPath, ignore_errors=True)
    return
  raise RuntimeWarning("Tried to remove directory not in path of DCSLM! " + str(dirPath))

def get_size_of_filelist(fileList):
  filelistSize = 0
  for dF in fileList:
    if os.path.isfile(dF):
      filelistSize += os.path.getsize(dF)
  return filelistSize

def get_size_of_directory(dirPath):
  dirSize = 0
  if os.path.isdir(dirPath):
    dirFiles = glob.glob(dirPath + "/**/*", recursive=True)
    dirSize += get_size_of_filelist(dirFiles)
  return dirSize

def remove_readonly(func, path, _):
  os.chmod(path, stat.S_IWRITE)
  func(path)

def determine_livery_string_location(liveryStr):
  if not liveryStr or len(liveryStr) == 0:
    return None
  if str.isnumeric(liveryStr) or "digitalcombatsimulator.com" in liveryStr:
    return "DCSUF"
  liveryPath = os.path.normpath(liveryStr)
  if os.path.isfile(liveryPath):
    return "Archive"
  return None
