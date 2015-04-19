from collections import OrderedDict
from itertools import zip_longest
from enum import Enum

class BaseField:
    def __init__(self, type, volatile=False):
        self.type = type
        self.volatile = volatile
        self.sub = issubclass(type, Node)
        if not (self.sub or self.type in (int, bool, str, bytes, float, complex, object) or issubclass(self.type, Enum)):
            raise TypeError("weird field type {}".format(self.type))

    def __get__(self, obj, type=None):
        return self.slot.__get__(obj, type)

    def __set__(self, obj, val):
        if not self.typecheck(val):
            raise TypeError("wrong type for {}.{}: wanted {}, got {}".format(
                self.cls.__name__,
                self.name,
                self.type.__name__,
                val
            ))
        if not self.volatile and hasattr(obj, self.name):
            raise TypeError("field already set")
        self.slot.__set__(obj, val)

    def __delete__(self, obj):
        raise TypeError("cannot delete node attribute")

class Field(BaseField):
    def typecheck(self, val):
        return isinstance(val, self.type)

    def subprocess(self, val, process):
        if self.sub:
            return process(val)
        else:
            return val

class MaybeField(BaseField):
    def typecheck(self, val):
        return isinstance(val, self.type) or val is None

    def subprocess(self, val, process):
        if self.sub and val is not None:
            return process(val)
        else:
            return val

class ListField(BaseField):
    def typecheck(self, val):
        if not isinstance(val, list):
            return False
        return all(isinstance(x, self.type) for x in val)

    def subprocess(self, val, process):
        if self.sub:
            return [process(x) for x in val]
        else:
            return val

class DictField(BaseField):
    def __init__(self, keytype, type):
        self.keytype = keytype
        super().__init__(type)

    def typecheck(self, val):
        if not isinstance(val, dict):
            return False
        return all(isinstance(k, self.keytype) and isinstance(v, self.type) for k, v in val.items())

    def subprocess(self, val, process):
        if self.sub:
            return {k: process(v) for k, v in val.items()}
        else:
            return val


class NodeMeta(type):
    def __prepare__(name, bases, abstract=False):
        return OrderedDict()

    def __new__(meta, name, bases, namespace, abstract=False):
        for base in bases:
            if not issubclass(base, Node):
                raise TypeError("base not derived from node")
        if '__slots__' in namespace:
            raise TypeError("__slots__ already present")
        fields = []
        for k, v in namespace.items():
            if isinstance(v, BaseField):
                v.name = k
                fields.append(v)
        for field in fields:
            del namespace[field.name]
        namespace['__slots__'] = [field.name for field in fields]
        cls = super().__new__(meta, name, bases, namespace)
        for field in fields:
            field.cls = cls
            field.slot = getattr(cls, field.name)
            setattr(cls, field.name, field)
        cls._fields = cls._fields + fields
        cls._abstract = abstract
        return cls

    def __init__(meta, name, bases, namespace, abstract=False):
        return super().__init__(name, bases, namespace)


class Node(metaclass=NodeMeta, abstract=True):
    _fields = []

    def __init__(self, *args):
        if self._abstract:
            raise TypeError("instantiating an abstract node type")
        if len(args) > len(self._fields):
            raise ValueError("arg and field counts don't match")
        for field, val in zip_longest(self._fields, args):
            setattr(self, field.name, val)

    def subprocess(self, process):
        return type(self)(*[
            field.subprocess(getattr(self, field.name), process)
            for field in self._fields
        ])

    def __eq__(self, other):
        return type(self) is type(other) and all(
            getattr(self, field.name) == getattr(other, field.name)
            for field in self._fields
        )
