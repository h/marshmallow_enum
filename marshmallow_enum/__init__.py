from __future__ import unicode_literals

import logging
import sys
import warnings
from enum import Enum

from marshmallow import ValidationError
from marshmallow.fields import Field

PY2 = sys.version_info.major == 2
# ugh Python 2
if PY2:
    string_types = (str, unicode)  # noqa: F821
    text_type = unicode  # noqa: F821
else:
    string_types = (str, )
    text_type = str

logger = logging.getLogger(__name__)


class LoadDumpOptions(Enum):
    ''' Deprecated: Use the by_value parameter instead '''
    value = 1
    name = 0


class EnumField(Field):
    VALUE = LoadDumpOptions.value  # deprecated
    NAME = LoadDumpOptions.name  # deprecated

    default_error_messages = {
        'by_name': 'Invalid enum member {input}',
        'by_value': 'Invalid enum value {input}',
        'must_be_string': 'Enum name must be string'
    }

    def __init__(self, enum_type, by_value=None, load_by=None, dump_by=None,
                 error="", *args, **kwargs):
        '''
        The `load_by` and `dump_by` parameters are deprecated. Use the `by_value` parameter instead.

        '''

        if by_value is None:
            if load_by is not None:
                if dump_by is not None and load_by != dump_by:
                    raise ValueError(
                        'Deprecated `load_by` parameter must not differ from `dump_by` parameter')
                by_value = (load_by == LoadDumpOptions.value)
            elif dump_by is not None:
                by_value = (dump_by == LoadDumpOptions.value)
            else:
                by_value = True

        if load_by is not None:
            logging.warning(
                'The `load_by` parameter is deprecated for '
                'marshmallow_enum.EnumField.__init__(). '
                'Use the `by_value` parameter instead')
            load_by_value = (load_by == LoadDumpOptions.value)
            if load_by_value != by_value:
                raise ValueError(
                    'Deprecated load_by_value parameter differs from by_value parameter')

        if dump_by is not None:
            logging.warning(
                'The `dump_by` parameter is deprecated for '
                'marshmallow_enum.EnumField.__init__(). '
                'Use the `by_value` parameter instead')
            dump_by_value = (dump_by == LoadDumpOptions.value)
            if dump_by_value != by_value:
                raise ValueError(
                    'Deprecated dump_by_value parameter differs from by_value parameter')

        if error and any(old in error for old in ('name}', 'value}', 'choices}')):
            warnings.warn(
                "'name', 'value', and 'choices' fail inputs are deprecated,"
                "use input, names and values instead",
                DeprecationWarning,
                stacklevel=2
            )

        self.enum = enum_type
        self.by_value = by_value
        self.error = error

        super(EnumField, self).__init__(*args, **kwargs)

        if not self.by_value:
            self.metadata['type'] = 'string'
        elif self.by_value:
            values = [e.value for e in self.enum if e.value is not None]
            if all(isinstance(v, int) for v in values):
                self.metadata['type'] = 'integer'
            elif all(isinstance(v, (float, int)) for v in values):
                self.metadata['type'] = 'number'
            elif all(isinstance(v, bool) for v in values):
                self.metadata['type'] = 'boolean'
            elif all(isinstance(v, str) for v in values):
                self.metadata['type'] = 'string'
        self.metadata['enum'] = sorted([
            e.value if self.by_value else e.name
            for e in self.enum
        ])

    def _serialize(self, value, attr, obj):
        if value is None:
            return None
        elif self.by_value:
            return value.value
        else:
            return value.name

    def _deserialize(self, value, attr, data, **kwargs):
        if value is None:
            return None
        elif self.by_value:
            return self._deserialize_by_value(value, attr, data)
        else:
            return self._deserialize_by_name(value, attr, data)

    def _deserialize_by_value(self, value, attr, data):
        try:
            return self.enum(value)
        except ValueError:
            self.fail('by_value', input=value, value=value)

    def _deserialize_by_name(self, value, attr, data):
        if not isinstance(value, string_types):
            self.fail('must_be_string', input=value, name=value)

        try:
            return getattr(self.enum, value)
        except AttributeError:
            self.fail('by_name', input=value, name=value)

    def fail(self, key, **kwargs):
        kwargs['values'] = ', '.join([text_type(mem.value) for mem in self.enum])
        kwargs['names'] = ', '.join([mem.name for mem in self.enum])

        if self.error:
            if self.by_value:
                kwargs['choices'] = kwargs['values']
            else:
                kwargs['choices'] = kwargs['names']
            msg = self.error.format(**kwargs)
            raise ValidationError(msg)
        else:
            super(EnumField, self).fail(key, **kwargs)
