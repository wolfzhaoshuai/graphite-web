"""Base tag database"""
import abc
import re

from django.conf import settings
from django.core.cache import cache

from graphite.tags.utils import TaggedSeries
from graphite.util import logtime


class BaseTagDB(object):
  __metaclass__ = abc.ABCMeta

  def __init__(self):
    """Initialize the tag db."""
    pass

  @logtime(custom_msg=True, custom_name=True)
  def find_series(self, tags, msg_setter, name_setter):
    """
    Find series by tag, accepts a list of tag specifiers and returns a list of matching paths.

    Tags specifiers are strings, and may have the following formats:

    .. code-block:: none

      tag=spec    tag value exactly matches spec
      tag!=spec   tag value does not exactly match spec
      tag=~value  tag value matches the regular expression spec
      tag!=~spec  tag value does not match the regular expression spec

    Any tag spec that matches an empty value is considered to match series that don't have that tag.

    At least one tag spec must require a non-empty value.

    Regular expression conditions are treated as being anchored at the start of the value.

    Matching paths are returned as a list of strings.
    """
    name_setter('%s.%s.find_series' % (self.__module__, self.__class__.__name__))

    cacheKey = 'TagDB.find_series:' + ':'.join(sorted(tags))
    result = cache.get(cacheKey)
    if result is not None:
      msg_setter('completed (cached) in')
    else:
      result = self._find_series(tags)
      cache.set(cacheKey, result, settings.TAGDB_CACHE_DURATION)

    return result

  @abc.abstractmethod
  def _find_series(self, tags):
    """
    Internal function called by find_series, follows the same semantics allowing base class to implement caching
    """
    pass

  @abc.abstractmethod
  def get_series(self, path):
    """
    Get series by path, accepts a path string and returns a TaggedSeries object describing the series.

    If the path is not found in the TagDB, returns None.
    """
    pass

  @abc.abstractmethod
  def list_tags(self, tagFilter=None):
    """
    List defined tags, returns a list of dictionaries describing the tags stored in the TagDB.

    Each tag dict contains the key "tag" which holds the name of the tag.  Additional keys may be returned.

    .. code-block:: none

      [
        {
          'tag': 'tag1',
        },
      ]

    Accepts an optional filter parameter which is a regular expression used to filter the list of returned tags
    """
    pass

  @abc.abstractmethod
  def get_tag(self, tag, valueFilter=None):
    """
    Get details of a particular tag, accepts a tag name and returns a dict describing the tag.

    The dict contains the key "tag" which holds the name of the tag.  It also includes a "values" key,
    which holds a list of the values for each tag.  See list_values() for the structure of each value.

    .. code-block:: none

      {
        'tag': 'tag1',
        'values': [
          {
            'value': 'value1',
            'count': 1,
          }
        ],
      }

    Accepts an optional filter parameter which is a regular expression used to filter the list of returned tags
    """
    pass

  @abc.abstractmethod
  def list_values(self, tag, valueFilter=None):
    """
    List values for a particular tag, returns a list of dictionaries describing the values stored in the TagDB.

    Each value dict contains the key "value" which holds the value, and the key "count" which is the number of
    series that have that value.  Additional keys may be returned.

    .. code-block:: none

      [
        {
          'value': 'value1',
          'count': 1,
        },
      ]

    Accepts an optional filter parameter which is a regular expression used to filter the list of returned tags
    """
    pass

  @abc.abstractmethod
  def tag_series(self, series):
    """
    Enter series into database.  Accepts a series string, upserts into the TagDB and returns the canonicalized series name.
    """
    pass

  @abc.abstractmethod
  def del_series(self, series):
    """
    Remove series from database.  Accepts a series string and returns True
    """
    pass

  @staticmethod
  def parse(path):
    return TaggedSeries.parse(path)

  @staticmethod
  def parse_tagspec(tagspec):
    m = re.match('^([^;!=]+)(!?=~?)([^;]*)$', tagspec)
    if m is None:
      raise ValueError("Invalid tagspec %s" % tagspec)

    tag = m.group(1)
    operator = m.group(2)
    spec = m.group(3)

    return (tag, operator, spec)
