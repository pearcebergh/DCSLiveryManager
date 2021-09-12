import requests
import patoolib
from bs4 import BeautifulSoup
from .Livery import DCSUserFile
from .UnitConfig import Units
from .Utilities import correct_dcs_user_files_url

# TODO: Make and expose config for parsing divs for info
class DCSUFParser():
  def __init__(self):
    self.DCSDownloadUrlPrefix = "https://www.digitalcombatsimulator.com"
    return

  def _get_aircraft_config_from_name(self, aircraftText):
    global AircraftConfigs
    lowerAircraftText = str.lower(aircraftText)
    for aircraft, config in Units.Units['aircraft'].items():
      if lowerAircraftText == str.lower(config['dcs_files']):
        return aircraft, config
      for n in config['names']:
        if str.lower(n) == lowerAircraftText:
          return aircraft, config
    return None, None

  def _remove_bad_filename_characters(self, filename):
    badFilenameCharacters = ['/', '\\', '?', '|', '*', '\"', '<', '>', ':']
    correctFilename = filename
    for c in badFilenameCharacters:
      correctFilename = correctFilename.replace(c, '')
    return " ".join(correctFilename.split()) # Remove extra spaces

  def _get_dcsfiles_archive_url_from_html(self, parsedHTML):
    downloadClass = parsedHTML.find(class_="btn btn-primary download")
    if downloadClass:
      fullArchiveUrl = self.DCSDownloadUrlPrefix + downloadClass['href']
      archiveType = '.' + str.split(fullArchiveUrl, '.')[-1]
      if archiveType in patoolib.ArchiveFormats:
        return fullArchiveUrl
      else:
        raise RuntimeError(fullArchiveUrl + " is not a valid url to an archive file.")

  def _request_html_from_url(self, url):
    try:
      r = requests.get(url)
      dcsufHTML = BeautifulSoup(r.text, 'html.parser')
      return dcsufHTML
    except:
      raise RuntimeError("Unable to request html from url " + url)

  def _parse_html_for_dcsuf(self, url, dcsufHTML):
    try:
      dcsuf = DCSUserFile()
      fileType = dcsufHTML.select_one("body > div.container > div.row.well > div.row.file-body > div.col-xs-10 > div.row.file-data-1 > div.col-xs-3.type > a").text
      if fileType == "Skin":
        fileURL = self._get_dcsfiles_archive_url_from_html(dcsufHTML)
        if fileURL:
          aircraftText = dcsufHTML.select_one("body > div.container > div.row.well > div.row.file-head.file-type-skn > div:nth-child(2) > span")
          if not aircraftText:
            aircraftText = dcsufHTML.select_one("body > div.container > div.row.well > div.row.file-head.file-type-skin > div:nth-child(2) > span")
          aircraftText = aircraftText.text
          aircraftGeneric, aircraftConfig = self._get_aircraft_config_from_name(aircraftText)
          dcsuf.id = dcsuf.get_id_from_url(url)
          dcsuf.unit = aircraftGeneric
          dcsuf.author = dcsufHTML.select_one("body > div.container > div.row.well > div.row.file-body > div.col-xs-10 > div.row.file-data-1 > div.col-xs-3.author > a").text
          titleText = dcsufHTML.select_one("body > div.container > div.row.well > div.row.file-body > div.col-xs-10 > div:nth-child(1) > div > h2").text
          dcsuf.title = self._remove_bad_filename_characters(titleText)
          dateText = dcsufHTML.select_one("body > div.container > div.row.well > div.row.file-body > div.col-xs-10 > div.row.file-data-1 > div.col-xs-3.date").text
          dateText = str.strip(dateText)
          dateText = dateText[dateText.find('-') + 2:]
          dcsuf.date = dateText
          dcsuf.datetime = dcsuf.date_to_datetime(dcsuf.date)
          dcsuf.size = dcsufHTML.select_one("body > div.container > div.row.well > div.row.file-body > div.col-xs-10 > div.row.file-data-2 > ul > li:nth-child(3)").contents[-1].strip()
          dcsuf.download = fileURL
          return dcsuf
      else:
        raise RuntimeError("Provided DCS User files url is not a livery skin file.")
    except:
      raise RuntimeError("Unable to parse html from " + url)

  def get_dcsuserfile_from_url(self, url):
    correctedURL, id = correct_dcs_user_files_url(url)
    if len(correctedURL):
      dcsufHTML = self._request_html_from_url(correctedURL)
      dcsuf = self._parse_html_for_dcsuf(correctedURL, dcsufHTML)
      return dcsuf
    return None
