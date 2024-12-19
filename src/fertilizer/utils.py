def flatten(arg):
  if not isinstance(arg, list):
    return [arg]
  return [x for sub in arg for x in flatten(sub)]


def url_join(*args):
  return "/".join([str(arg).strip("/") for arg in args if str(arg).strip("/")])
