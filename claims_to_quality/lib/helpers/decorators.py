"""Useful decorators."""
import functools


def override(function):
    """
    A decorator to indicate that a function has been overridden from its parent class.

    Attempts to inspect the function from the parent class, raising an error if the parent class
    does not have a function of the same name.
    """
    # TODO: Audit the codebase for overridden methods and apply this decorator.
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        instance = args[0]
        getattr(super(instance.__class__, instance), function.__name__)
        return function(*args, **kwargs)
    return wrapper
