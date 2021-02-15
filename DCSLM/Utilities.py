
def correct_dcs_user_files_url(fileURL):
  DCSFilesURLRoot = "https://www.digitalcombatsimulator.com/en/files/"
  if fileURL[-1] == '/':
    fileURL = fileURL[:-1]
  splitFileURL = str.split(fileURL, "/")[-1] # strip down url to just the ID
  if str.isnumeric(splitFileURL): # check if it's ID-like
    return DCSFilesURLRoot + splitFileURL + "/" # put it back together
  return None
