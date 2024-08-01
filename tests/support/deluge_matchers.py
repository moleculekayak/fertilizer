def deluge_matcher(request, method):
  if request.json().get("method") == method:
    return True
  return None


def auth_matcher(request):
  return deluge_matcher(request, "auth.login")


def connected_matcher(request):
  return deluge_matcher(request, "web.connected")


def label_plugin_matcher(request):
  return deluge_matcher(request, "core.get_enabled_plugins")


def torrent_info_matcher(request):
  return deluge_matcher(request, "web.update_ui")


def add_torrent_matcher(request):
  return deluge_matcher(request, "core.add_torrent_file")


def get_labels_matcher(request):
  return deluge_matcher(request, "label.get_labels")


def add_label_matcher(request):
  return deluge_matcher(request, "label.add")


def apply_label_matcher(request):
  return deluge_matcher(request, "label.set_torrent")
