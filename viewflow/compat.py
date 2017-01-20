"""Django compatibility utils."""
from functools import WRAPPER_ASSIGNMENTS, update_wrapper

try:
    from unittest import mock  # NOQA
except ImportError:
    import mock  # NOQA

try:
    from django.utils.module_loading import import_string  # NOQA
except:
    # django 1.6/1.7
    from django.utils.module_loading import import_by_path as import_string  # NOQA

try:
    from django.template.library import TemplateSyntaxError, TagHelperNode, parse_bits  # NOQA
except:
    from django.template.base import TemplateSyntaxError, Node, parse_bits  # NOQA

    class TagHelperNode(Node):
        """
        Base class for tag helper nodes such as SimpleNode and InclusionNode.

        Manages the positional and keyword arguments to be passed to the decorated
        function.
        """

        def __init__(self, func, takes_context, args, kwargs):  # noqa D102
            self.func = func
            self.takes_context = takes_context
            self.args = args
            self.kwargs = kwargs

        def get_resolved_arguments(self, context):
            """Resolve all args from the template context."""
            resolved_args = [var.resolve(context) for var in self.args]
            if self.takes_context:
                resolved_args = [context] + resolved_args
            resolved_kwargs = {k: v.resolve(context) for k, v in self.kwargs.items()}
            return resolved_args, resolved_kwargs

try:
    # djagno 1.7
    from django.apps import apps
    from django.utils.deconstruct import deconstructible  # NOQA
    from django.utils.module_loading import autodiscover_modules  # NOQA

    def get_app_package(app_label):
        """Return app package string."""
        app_config = apps.get_app_config(app_label)
        if not app_config:
            return None
        return app_config.module.__name__

    def get_containing_app_data(module):
        """Return app label and package string."""
        app_config = apps.get_containing_app_config(module)
        if not app_config:
            return None, None
        return app_config.label, app_config.module.__name__

    def manager_from_queryset(manager_class, queryset_class, class_name=None):
        """Return a subclass of your base Manager with a copy of the custom QuerySet methods."""
        return manager_class.from_queryset(queryset_class, class_name=class_name)

except ImportError:
    # djagno 1.6 backport
    import inspect
    from django.db.models import loading
    from django.utils import six

    def get_app_package(app_label):
        """Get package by app_label."""
        app_config = loading.get_app(app_label)
        if not app_config:
            return None
        if app_config.__package__ is None:
            app_config.__package__ = app_config.__name__.rpartition('.')[0]
        if app_config.__package__.endswith('.models'):
            return app_config.__package__[0:-len('.models')]
        return app_config.__package__

    def _get_containing_app_package(object_name):
        candidates = []
        for app_config in loading.get_apps():
            if app_config.__package__ is None:
                app_config.__package__ = app_config.__name__.rpartition('.')[0]

            if app_config.__package__.endswith('.models'):
                package = app_config.__package__[0:-len('.models')]
            else:
                package = app_config.__package__

            if object_name.startswith(package):
                subpath = object_name[len(package):]
                if subpath == '' or subpath[0] == '.':
                    candidates.append(package)
        if candidates:
            return sorted(candidates, key=lambda ac: -len(ac))[0]

    def get_containing_app_data(object_name):
        """Return pair (app_label, package)."""
        package = _get_containing_app_package(object_name)
        if package:
            return package.rsplit('.', 1)[-1], package
        return None, None

    def deconstructible(cls):
        """Deconstructible decorator stub."""
        return cls

    def autodiscover_modules(*args, **kwargs):
        """Auto-discover INSTALLED_APPS modules ."""
        import copy
        from django.conf import settings
        from django.utils.importlib import import_module
        from django.utils.module_loading import module_has_submodule

        register_to = kwargs.get('register_to')

        for app in settings.INSTALLED_APPS:
            mod = import_module(app)

            for module_to_search in args:
                if register_to:
                    before_import_registry = copy.copy(register_to._registry)

                try:
                    import_module('%s.%s' % (app, module_to_search))
                except:
                    if register_to:
                        register_to._registry = before_import_registry

                    if module_has_submodule(mod, module_to_search):
                        raise

    def _get_queryset_methods(manager_class, queryset_class):
        def create_method(name, method):
            def manager_method(self, *args, **kwargs):
                return getattr(self.get_queryset(), name)(*args, **kwargs)
            manager_method.__name__ = method.__name__
            manager_method.__doc__ = method.__doc__
            return manager_method

        new_methods = {}
        # Refs http://bugs.python.org/issue1785.
        predicate = inspect.isfunction if six.PY3 else inspect.ismethod
        for name, method in inspect.getmembers(queryset_class, predicate=predicate):
            # Only copy missing methods.
            if hasattr(manager_class, name):
                continue
            # Only copy public methods or methods with the attribute `queryset_only=False`.
            queryset_only = getattr(method, 'queryset_only', None)
            if queryset_only or (queryset_only is None and name.startswith('_')):
                if name != '_update':  # django 1.6 have no queryset_only attrubutes on methods
                    continue
            elif name == 'delete':
                continue
            # Copy the method onto the manager.
            new_methods[name] = create_method(name, method)

        # Fix get_queryset
        def get_queryset(self):
            return self._queryset_class(self.model, using=self._db)
        new_methods['get_queryset'] = get_queryset
        return new_methods

    def manager_from_queryset(manager_class, queryset_class, class_name=None):
        """Return a subclass of your base Manager with a copy of the custom QuerySet methods."""
        if class_name is None:
            class_name = '%sFrom%s' % (manager_class.__name__, queryset_class.__name__)
        class_dict = {
            '_queryset_class': queryset_class,
        }
        class_dict.update(_get_queryset_methods(manager_class, queryset_class))
        return type(class_name, (manager_class,), class_dict)


def get_all_related_objects(obj):
    """Backward releations to a model."""
    if hasattr(obj._meta, 'get_fields'):
        from django.db.models.fields.related import ForeignObjectRel
        return [field for field in obj._meta.get_fields() if isinstance(field, ForeignObjectRel)]
    else:
        # depricated in django 1.9
        return obj._meta.get_all_related_objects()

"""
Backbort method decorator from django 1.10 to django 1.8
"""


def available_attrs(fn):
    """
    Return the list of functools-wrappable attributes on a callable.
    This was required as a workaround for http://bugs.python.org/issue3445
    under Python 2.
    """
    return WRAPPER_ASSIGNMENTS


def method_decorator(decorator, name=''):
    """
    Converts a function decorator into a method decorator
    """
    # 'obj' can be a class or a function. If 'obj' is a function at the time it
    # is passed to _dec,  it will eventually be a method of the class it is
    # defined on. If 'obj' is a class, the 'name' is required to be the name
    # of the method that will be decorated.
    def _dec(obj):
        is_class = isinstance(obj, type)
        if is_class:
            if name and hasattr(obj, name):
                func = getattr(obj, name)
                if not callable(func):
                    raise TypeError(
                        "Cannot decorate '{0}' as it isn't a callable "
                        "attribute of {1} ({2})".format(name, obj, func)
                    )
            else:
                raise ValueError(
                    "The keyword argument `name` must be the name of a method "
                    "of the decorated class: {0}. Got '{1}' instead".format(
                        obj, name,
                    )
                )
        else:
            func = obj

        def decorate(function):
            """
            Apply a list/tuple of decorators if decorator is one. Decorator
            functions are applied so that the call order is the same as the
            order in which they appear in the iterable.
            """
            if hasattr(decorator, '__iter__'):
                for dec in decorator[::-1]:
                    function = dec(function)
                return function
            return decorator(function)

        def _wrapper(self, *args, **kwargs):
            @decorate
            def bound_func(*args2, **kwargs2):
                return func.__get__(self, type(self))(*args2, **kwargs2)
            # bound_func has the signature that 'decorator' expects i.e.  no
            # 'self' argument, but it is a closure over self so it can call
            # 'func' correctly.
            return bound_func(*args, **kwargs)
        # In case 'decorator' adds attributes to the function it decorates, we
        # want to copy those. We don't have access to bound_func in this scope,
        # but we can cheat by using it on a dummy function.

        @decorate
        def dummy(*args, **kwargs):
            pass
        update_wrapper(_wrapper, dummy)
        # Need to preserve any existing attributes of 'func', including the name.
        update_wrapper(_wrapper, func)

        if is_class:
            setattr(obj, name, _wrapper)
            return obj

        return _wrapper
    # Don't worry about making _dec look similar to a list/tuple as it's rather
    # meaningless.
    if not hasattr(decorator, '__iter__'):
        update_wrapper(_dec, decorator, assigned=available_attrs(decorator))
    # Change the name to aid debugging.
    if hasattr(decorator, '__name__'):
        _dec.__name__ = 'method_decorator(%s)' % decorator.__name__
    else:
        _dec.__name__ = 'method_decorator(%s)' % decorator.__class__.__name__
    return _dec
