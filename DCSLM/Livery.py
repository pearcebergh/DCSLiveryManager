import json
import os
from datetime import datetime
import DCSLM.Utilities as Utilities
from DCSLM.UnitManager import UM
from DCSLM.Unit import Unit

class DCSUserFile:
  def __init__(self):
    self.id = None
    self.unit = []
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
      'unit': [u.generic for u in self.unit],
      'author': self.author,
      'title': self.title,
      'date': self.date,
      'datetime': datetime.timestamp(self.datetime) if self.datetime else None,
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
          elif var == 'unit':
            if type(jsonData['unit']) is list:
              unitList = [UM.get_unit_from_generic_name(u) for u in jsonData['unit']]
              setattr(self, var, unitList)
            else:
              setattr(self, var, [UM.get_unit_from_generic_name(jsonData['unit'])])
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

  def get_units_friendly_string(self):
    return ", ".join([u.friendly for u in self.unit])

  def get_units_generic_string(self):
    return ", ".join([u.generic for u in self.unit])

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

  def datetime_to_date(self, dt):
    if dt:
      return dt.strftime('%m/%d/%Y %H:%M:%S')
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
      elif var == "installs":
        jsonLivery[var] = {'units': [], 'liveries': selfVars[var]['liveries'], 'optimized': selfVars[var]['optimized'] }
        for u in selfVars[var]['units']:
          if isinstance(u, str):
            jsonLivery[var]['units'].append(u)
          elif isinstance(u, Unit):
            jsonLivery[var]['units'].append(u.generic)
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
    if self.dcsuf and len(self.dcsuf.unit) and self.dcsuf.title:
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
