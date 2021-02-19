from . import Livery
from . import UnitConfig
import os, sys

class LiveryManager:
  def __init__(self):
    self.LiveryData = self.make_default_data()

  def make_default_data(self):
    ld = {
      "config": {
        "ovgme": False
      },
      "liveries": {}
    }
    return ld

  def load_data(self):
    return None

  def write_data(self):
    return None

  def prompt_default_data(self):
    # Make user prompts for some of the default config settings
    return None

  def get_registered_livery(self, id=None, livery=None):
    userID = id
    if livery:
      userID = livery.id
    if userID:
      if userID in self.LiveryData["liveries"].keys():
        return self.LiveryData["liveries"][userID]
    return None

  def is_livery_registered(self, id=None, livery=None):
    if self.get_registered_livery(id, livery):
      return True
    return False

  def register_livery(self, livery):
    if livery:
      if not self.is_livery_registered(livery.id):
        self.LiveryData["liveries"][livery.id] = livery
        return self.LiveryData["liveries"][livery.id]
    return None

  def unregister_livery(self, livery):
    if livery:
      if self.is_livery_registered(livery.id):
        del self.LiveryData["liveries"][livery.id]
        return True
    return False

  def write_livery_registry_file(self, livery):
    return None

  def remove_livery_registry_file(self, livery):
    return None

  def download_livery_archive(self, livery):
    if livery:
      return True
    return False

  def extract_livery_archive(self, livery):
    if livery:
      return True
    return False

  def detect_extracted_liveries(self, livery, extractPath):
    if livery:
      return True
    return False

  def move_detected_liveries(self, livery, extractPath, detectedLiveries):
    if livery:
      return True
    return False

  def remove_extracted_livery_archive(self, livery, extractPath):
    if livery:
      return True
    return False

  def remove_downloaded_archive(self, livery, downloadPath):
    if livery:
      return True
    return False
