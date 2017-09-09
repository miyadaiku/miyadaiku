import collections
import enum

HOOKS = enum.Enum('HOOKS', (
    'start', 'initialized', 'pre_load', 'post_load', 'loaded',
    'pre_build', 'post_build', 'finished',))

hooks = collections.defaultdict(list)


def run_hook(hook, *args, **kwargs):
    assert isinstance(hook, HOOKS)

    for h in hooks[hook]:
        h(*args, **kwargs)


def start(f):
    hooks[HOOKS.start].append(f)
    return f


def initialized(f):
    hooks[HOOKS.initialized].append(f)
    return f


def pre_load(f):
    hooks[HOOKS.pre_load].append(f)
    return f


def post_load(f):
    hooks[HOOKS.post_load].append(f)
    return f


def loaded(f):
    hooks[HOOKS.loaded].append(f)
    return f


def pre_build(f):
    hooks[HOOKS.pre_build].append(f)
    return f


def post_build(f):
    hooks[HOOKS.post_build].append(f)
    return f


def finished(f):
    hooks[HOOKS.finished].append(f)
    return f
