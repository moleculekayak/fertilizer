def flatten(arg):
    if not isinstance(arg, list):
        return [arg]
    return [x for sub in arg for x in flatten(sub)]
