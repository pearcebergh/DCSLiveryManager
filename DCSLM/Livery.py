from .Utilities import correct_dcs_user_files_url


class DCSUserFile:
  def __init__(self):
    self.id = None
    self.unit = None
    self.author = None
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


class Livery:
  def __init__(self):
    self.unit = None
    self.title = None
    self.archive = None
    self.ovgme = None
    self.destination = None
    self.dcsuf = None

  def generate_ovgme_folder(self):
    if (self.dcsuf or self.title) and self.unit:
      return "OVGME blah"
    else:
      raise RuntimeError("Unable to generate OVGME folder for livery due to insufficient data.")
