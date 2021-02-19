from .Utilities import correct_dcs_user_files_url

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

  def get_id_from_url(self, fileURL):
    try:
      return str.split(fileURL, '/')[-1]
    except:
      RuntimeError("Unable to get ID from url \'" + fileURL + "\'")

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
    self.download = "69_Vipenation_FS_Livery_v3.zip"

class Livery:
  def __init__(self):
    self.unit = None
    self.title = None
    self.archive = None
    self.ovgme = None
    self.destination = None
    self.dcsuf = DCSUserFile()
    self.install = []

  def generate_ovgme_folder(self):
    if (self.dcsuf or self.title) and self.unit:
      titleText = ""
      if self.title:
        titleText = self.title
      elif self.dcsuf:
        titleText = self.dcsuf.title
      return self.unit + " - " + titleText
    else:
      raise RuntimeError("Unable to generate OVGME folder for livery due to insufficient data.")

  def _fill_data_test(self):
    self.dcsuf = DCSUserFile()
    self.dcsuf._fill_data_test()
    self.unit = self.dcsuf.unit
    self.title = self.dcsuf.title
    self.ovgme = self.generate_ovgme_folder()
    self.archive = "/DCSLM/archives/" + self.dcsuf.download
    self.destination = "/Liveries/"
