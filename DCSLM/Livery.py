import json
import os
from datetime import datetime
import DCSLM.UnitManager as UnitManager
import DCSLM.Utilities as Utilities

class DCSUserFile:
  def __init__(self):
    self.id = None
    self.unit = None
    self.author = None
    self.title = None
    self.date = None
    self.datetime = None
    self.size = None
    self.download = None
    self.tags = None

  def to_JSON(self):
    return {
      'id': self.id,
      'unit': self.unit,
      'author': self.author,
      'title': self.title,
      'date': self.date,
      'datetime': datetime.timestamp(self.datetime),
      'size': self.size,
      'download': self.download,
      'tags': self.tags,
    }

  def from_JSON(self, jsonData):
    if jsonData:
      classVars = vars(DCSUserFile())
      for var, data in classVars.items():
        if var in jsonData.keys():
          if var == 'datetime':
            setattr(self, var, datetime.fromtimestamp(jsonData['datetime']))
          else:
            setattr(self, var, jsonData[var])
      return self

  def from_JSON_String(self, jsonStr):
    jsonData = json.loads(jsonStr)
    if jsonData:
      return self.from_JSON(jsonData)

  def get_id_from_url(self, fileURL):
    if fileURL:
      splitURL = str.split(fileURL, '/')
      for s in splitURL:
        if s.isnumeric():
          return int(s)
    raise RuntimeWarning("Unable to get DCS User File ID from url " + fileURL)

  def date_to_datetime(self, date):
    if len(date):
      if '/' in date: # EN
        return datetime.strptime(date, '%m/%d/%Y %H:%M:%S')
      elif '.' in date: # RU, DE, FR, IT
        return datetime.strptime(date, '%d.%m.%Y %H:%M:%S')
      elif '-' in date: # CN
        return datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
      else:
        raise RuntimeError("Unable to parse date text \'" + date + "\' to datetime object.")
    return None

  def datetime_to_date(self, datetime):
    if datetime:
      return datetime.strftime('%m/%d/%Y %H:%M:%S')
    return ""

class Livery:
  def __init__(self):
    self.archive = None
    self.ovgme = None
    self.destination = None
    self.dcsuf = DCSUserFile()
    self.installs = { 'units': [], 'liveries': {}, 'optimized': False }

  def to_JSON(self):
    liveryVars = vars(Livery())
    selfVars = vars(self)
    jsonLivery = {}
    for var in liveryVars.keys():
      if var == "dcsuf":
        jsonLivery[var] = selfVars[var].to_JSON()
      else:
        jsonLivery[var] = selfVars[var]
    return jsonLivery

  def from_JSON(self, jsonData):
    if jsonData:
      liveryVars = vars(Livery())
      for var, data in liveryVars.items():
        if var in jsonData.keys():
          if var == "dcsuf":
            setattr(self, var, DCSUserFile().from_JSON(jsonData[var]))
          else:
            setattr(self, var, jsonData[var])
    return self

  def from_JSON_String(self, jsonStr):
    jsonData = json.loads(jsonStr)
    return self.from_JSON(jsonData)

  def generate_ovgme_folder(self):
    if self.dcsuf and self.dcsuf.unit and self.dcsuf.title:
      return self.dcsuf.title
    else:
      raise RuntimeError("Unable to generate OVGME folder name for livery due to insufficient data.")

  def get_num_liveries(self):
    liveryCount = 0
    for ac, data in self.installs['liveries'].items():
      liveryCount += len(data['paths'])
    return liveryCount

  def calculate_size_installed_liveries(self):
    for i, v in self.installs['liveries'].items():
      v['size'] = 0
      for p in v['paths']:
        v['size'] += Utilities.get_size_of_directory(os.path.join(os.getcwd(), self.destination, p))

  def get_size_installed_liveries(self):
    totalSize = 0
    for i, v in self.installs['liveries'].items():
      totalSize += v['size']
    return totalSize

  def is_optimized(self):
    return self.installs['optimized']
