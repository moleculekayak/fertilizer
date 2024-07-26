class Tracker:
  def source_flags():
    raise NotImplementedError
  
  def announce_url():
    raise NotImplementedError
  
class OpsTracker(Tracker):
  def source_flags():
    return (b"OPS", b"APL")
  
  def announce_url():
    return b"home.opsfet.ch"
  
class RedTracker(Tracker):
  def source_flags():
    return (b"RED", b"PTH")
  
  def announce_url():
    return b"flacsfor.me"
