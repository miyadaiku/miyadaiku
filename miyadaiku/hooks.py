from typing import DefaultDict, Callable, List, Any
import collections
import enum

HOOKS = enum.Enum('HOOKS', (
    'start', 'initialized', 'pre_load', 'post_load', 'loaded',
    'pre_build', 'post_build', 'finished',))


HookFunc = Callable[..., Any]

hooks:DefaultDict[HOOKS, List[HookFunc]] = collections.defaultdict(list)


def run_hook(hook:HOOKS , *args:Any, **kwargs:Any)->None:
    assert isinstance(hook, HOOKS)

    for h in hooks[hook]:
        h(*args, **kwargs)


def start(f:HookFunc)->HookFunc:
    hooks[HOOKS.start].append(f)
    return f


def initialized(f:HookFunc)->HookFunc:
    hooks[HOOKS.initialized].append(f)
    return f


def pre_load(f:HookFunc)->HookFunc:
    hooks[HOOKS.pre_load].append(f)
    return f


def post_load(f:HookFunc)->HookFunc:
    hooks[HOOKS.post_load].append(f)
    return f


def loaded(f:HookFunc)->HookFunc:
    hooks[HOOKS.loaded].append(f)
    return f


def pre_build(f:HookFunc)->HookFunc:
    hooks[HOOKS.pre_build].append(f)
    return f


def post_build(f:HookFunc)->HookFunc:
    hooks[HOOKS.post_build].append(f)
    return f


def finished(f:HookFunc)->HookFunc:
    hooks[HOOKS.finished].append(f)
    return f
