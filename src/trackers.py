class Tracker:
  @staticmethod
  def source_flags_for_search():
    raise NotImplementedError

  @staticmethod
  def source_flags_for_creation():
    raise NotImplementedError

  @staticmethod
  def announce_url():
    raise NotImplementedError

  @staticmethod
  def site_shortname():
    raise NotImplementedError

  @staticmethod
  def reciprocal_tracker():
    raise NotImplementedError


class OpsTracker(Tracker):
  @staticmethod
  def source_flags_for_search():
    return [b"OPS", b"APL"]

  @staticmethod
  def source_flags_for_creation():
    return [b"OPS", b"APL", b""]

  @staticmethod
  def announce_url():
    return b"home.opsfet.ch"

  @staticmethod
  def site_shortname():
    return "OPS"

  @staticmethod
  def reciprocal_tracker():
    return RedTracker


class RedTracker(Tracker):
  @staticmethod
  def source_flags_for_search():
    return [b"RED", b"PTH"]

  @staticmethod
  def source_flags_for_creation():
    return [b"RED", b"PTH", b""]

  @staticmethod
  def announce_url():
    return b"flacsfor.me"

  @staticmethod
  def site_shortname():
    return "RED"

  @staticmethod
  def reciprocal_tracker():
    return OpsTracker
