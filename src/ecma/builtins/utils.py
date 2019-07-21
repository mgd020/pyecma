def typeof(value):
    return type(value).__name__


class _Exception(Exception):
    pass


def update_var(name, operator, prefix, *contexts):
    # find it
    for context in contexts:
        try:
            pre_val = context[name]
            break
        except KeyError:
            pass
    else:
        raise NameError("name '%s' is not defined" % name)

    # update it
    if operator == "++":
        post_val = pre_val + 1
    elif operator == "--":
        post_val = pre_val - 1
    else:
        raise ValueError(operator)
    context[name] = post_val

    # return value
    if prefix:
        return post_val  # ++{name}
    return pre_val  # {name}++


def strictly_equal(a, b):
    return type(a) == type(b) and a == b


def enumerable_properties(var):
    # https://developer.mozilla.org/en-US/docs/Web/JavaScript/Enumerability_and_ownership_of_properties
    raise NotImplementedError
