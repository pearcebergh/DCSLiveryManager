from requests import get

def correct_dcs_user_files_url(fileURL):
  # TODO: Better url parsing as sometimes there is a trailing /?... in the url
  DCSFilesURLRoot = "https://www.digitalcombatsimulator.com/en/files/"
  if fileURL[-1] == '/':
    fileURL = fileURL[:-1]
  splitFileURL = str.split(fileURL, "/")[-1] # strip down url to just the ID
  if str.isnumeric(splitFileURL): # check if it's ID-like
    return DCSFilesURLRoot + splitFileURL + "/" # put it back together
  return None

def size_text_to_bytes(sizeText):
  if len(sizeText):
    if 'mb' in str.lower(sizeText):
      sizeText = sizeText.split(' ')[0]
    sizeInt = int(float(sizeText) * 100) * (10**4)
    return sizeInt
  return 0

def bytes_to_mb_string(sizeBytes):
  return "{:.2f}".format(float(sizeBytes/(10**6)))

def request_file_size(fileURL):
  return int(get(fileURL, stream=True).headers['Content-length'])
