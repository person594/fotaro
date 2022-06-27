from collections import namedtuple


SearchFilter = namedtuple('SearchFilter', ['name', 'description', 'fields', 'sql', 'callback'], defaults=({}, None, None))


SortBy = namedtuple('SortBy', ['name', 'description', 'fields', 'sql', 'sort_key'], defaults=({}, None, None))
