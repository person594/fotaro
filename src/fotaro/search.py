from collections import namedtuple
from .formulaic import formulaic, field, OneOfField, Option, SubmitField
from .component import Component

from typing import Optional
from datetime import datetime

SearchFilter = namedtuple('SearchFilter', ['name', 'description', 'fields', 'sql', 'callback'], defaults=({}, None, None))


#SortBy = namedtuple('SortBy', ['name', 'description', 'fields', 'sql', 'sort_key'], defaults=({}, None, None))


class SortBy:
    def __init__(self):
        ...

    @staticmethod
    def description():
        raise NotImplementedError

class SearchFilter:
    name = "true"
    def __init__():
        ...

    def get_clause(self):
        return "TRUE"
        
    def callback(self, photo):
        return True

class DateRange(SearchFilter):
    name = "date"
    def __init__(self, start_date: Optional[datetime], end_date: Optional[datetime] = None):
        super().__init__("date", "Date", "Find photos taken in a particular date range")
        self.start_time = start_date
        self.end_date = end_date

    def get_clause(self):
        s = "TIMESTAMP IS NOT NULL"
        if self.start_date is not None:
            start_timestamp = int(start_date.timestamp())
            s = f"{s} AND TIMESTAMP >= {start_timestamp}"
        if self.end_date is not None:
            end_timestamp = int(start_date.timestamp())
            s = f"{s} AND TIMESTAMP <= {end_timestamp}"
        return s

    def callback(self, photo):
        return True
    
class Union(SearchFilter):
    name = "or"
    def __init__(self, *filters):
        super().__init__("or", "Union", "Disjunction of filters")
        self.filters = list(filters)

    def get_clause(self):
        return " OR ".join([f"({f.get_clause()})" for f in self.filters])

    def callback(self, photo):
        for filter in self.filters:
            if filter.callback(photo):
                return True
        return False

class SortBy:
    def __init__(self, name, description):
        self.name = name
        self.description = description

    def get_form_html(self):
        raise NotImplementedError

    def callback(self, **kwargs):
        raise NotImplementedError

    
class Search(Component):
    def __init__(self, fo):
        self.fo = fo
        self.rec_search_filters = [DateRange, Union]
        self.rec_
        
    def parse_query(self, filter_query: list, sort_by_query: list):
        filters = {f.name: f for f in self.fo.rec_search_filters}
        if len(filter_query) < 1 or filter_query[0] not in filters:
            return None
        filter_class = filters[filter_query[0]]
        parsed_args = []
        for arg in filter_query[1:]:
            if isinstance(arg, list):
                parsed = self.parse_query(arg)
                if parsed is None:
                    return None
                parsed_args.append(parsed)
        try:
            search_filter = filter_class(*parsed_args)
        except:
            return None
