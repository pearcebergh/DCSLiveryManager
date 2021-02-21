from .Utilities import correct_dcs_user_files_url
from .UnitConfig import Units
import os
import json

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

  def to_JSON(self):
    return {
      'id': self.id,
      'unit': self.unit,
      'author': self.author,
      'title': self.title,
      'date': self.date,
      'datetime': self.datetime,
      'size': self.size,
      'download': self.download,
    }

  def from_JSON(self, jsonData):
    if jsonData:
      self.id = jsonData['id']
      self.unit = jsonData['unit']
      self.author = jsonData['author']
      self.title = jsonData['title']
      self.date = jsonData['date']
      self.datetime = jsonData['datetime']
      self.size = jsonData['size']
      self.download = jsonData['download']

  def from_JSON_String(self, jsonStr):
    jsonData = json.loads(jsonStr)
    if jsonData:
      self.from_JSON(jsonData)

  def get_id_from_url(self, fileURL):
    try:
      return str.split(fileURL, '/')[-1]
    except:
      RuntimeError("Unable to get ID from url \'" + fileURL + "\'")

  def date_to_datetime(self, date):
    return 0

  def datetime_to_date(self, datetime):
    return ""

  def fill_from_parsed_html(self, fileURL, parsedHTML):
    try:
      correctedFileURL = correct_dcs_user_files_url(fileURL)
      if correctedFileURL:
        print("Fill from " + correctedFileURL)
      else:
        raise NotImplementedError("Unable to get valid DCS Files URL from \'" + fileURL + "\'")
    except:
      RuntimeError("Unable to parse HTML for DCS User File class.")

  def _fill_data_test(self):
    self.id = 69420
    self.unit = "f-16c"
    self.author = "Sneep"
    self.title = "69th #VIPENATION FS Livery"
    self.date = "19.02.2021 03:24"
    self.datetime = 0
    self.size = "69.00 Mb"
    self.download = "https://www.digitalcombatsimulator.com/upload/iblock/079/69th_-_Vipenation_FS_v1.zip"

class Livery:
  def __init__(self):
    self.unit = None
    self.title = None
    self.archive = None
    self.ovgme = None
    self.destination = None
    self.dcsuf = DCSUserFile()
    self.install = []
    # install paths will be in the form of Units['aircraft'][self.aircraft]/livery_title/

  def to_JSON(self):
    return {
      'unit': self.unit,
      'title': self.title,
      'archive': self.archive,
      'ovgme': self.ovgme,
      'destination': self.destination,
      'dcsuf': self.dcsuf.to_JSON(),
      'install': self.install,
    }

  def from_JSON(self, jsonData):
    if jsonData:
      self.unit = jsonData['unit']
      self.title = jsonData['title']
      self.archive = jsonData['archive']
      self.ovgme = jsonData['ovgme']
      self.destination = jsonData['destination']
      self.dcsuf = DCSUserFile().from_JSON(jsonData['dcsuf'])
      self.install = jsonData['install']

  def from_JSON_String(self, jsonStr):
    jsonData = json.loads(jsonStr)
    if jsonData:
      self.from_JSON(jsonData)

  def generate_ovgme_folder(self):
    if (self.dcsuf or self.title) and self.unit:
      titleText = ""
      if self.title:
        titleText = self.title
      elif self.dcsuf:
        titleText = self.dcsuf.title
      return Units.Units['aircraft'][self.unit]['friendly'] + " - " + titleText
    else:
      raise RuntimeError("Unable to generate OVGME folder for livery due to insufficient data.")

  def _fill_data_test(self):
    self.dcsuf = DCSUserFile()
    self.dcsuf._fill_data_test()
    self.unit = self.dcsuf.unit
    self.title = self.dcsuf.title
    self.ovgme = self.generate_ovgme_folder()
    self.archive = "/DCSLM/archives/" + self.dcsuf.download.split('/')[-1]
    self.destination = "/Liveries/"
    self.install.append(os.path.join(Units.Units['aircraft'][self.unit]['liveries'][0], self.title))
