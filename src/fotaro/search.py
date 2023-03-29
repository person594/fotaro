from collections import namedtuple
from .formulaic import formulaic, field, OneOfField, Option, SubmitField
from .component import Component

from typing import Optional
from datetime import datetime

import dateutil

from flask import request, abort

from .cas import CAS

SearchFilter = namedtuple('SearchFilter', ['name', 'description', 'fields', 'sql', 'callback'], defaults=({}, None, None))


#SortBy = namedtuple('SortBy', ['name', 'description', 'fields', 'sql', 'sort_key'], defaults=({}, None, None))


class SortBy:
    def __init__(self):
        ...

    def get_clause(self):
        return None

    callback = None

    
class SearchFilter:
    name = "true"
    def __init__():
        ...

    def get_clause(self):
        return "TRUE"
        
    callback = None

class DateRange(SearchFilter):
    name = "date"
    def __init__(self, start_date: Optional[str], end_date: Optional[str] = None):
        try:
            self.start_date = dateutil.parse(start_date)
        except:
            self.start_date = None
        try:
            self.end_date = dateutil.parse(end_date)
        except:
            self.end_date = None

    def get_clause(self):
        s = "TIMESTAMP IS NOT NULL"
        if self.start_date is not None:
            start_timestamp = int(self.start_date.timestamp())
            s = f"{s} AND TIMESTAMP >= {start_timestamp}"
        if self.end_date is not None:
            end_timestamp = int(self.start_date.timestamp())
            s = f"{s} AND TIMESTAMP <= {end_timestamp}"
        return s
    
"""
class Union(SearchFilter):
    name = "or"
    def __init__(self, *filters):
        super().__init__("or", "Union", "Disjunction of filters")
        self.filters = list(filters)
        for filter in filters:
            if filter.callback is None:
                self.callback = None

    def get_clause(self):
        return " OR ".join([f"({f.get_clause()})" for f in self.filters])

    def callback(self, photo):
        for filter in self.filters:
            if filter.callback is None or filter.callback(photo):
                return True
        return False
"""
    
class Search(Component):
    def __init__(self, fo):
        self.fo = fo
        self.rec_search_filters = [DateRange]

    def setup(self):
        
        self.search(DateRange(datetime(2000, 1, 1)), SortBy())
        
        @self.fo.server.route("/searchResults", methods=["POST"])
        def serve_search_results():
            try:
                search_filter = request.json['search_filter']
                sort_by = request.json['sort_by']
            except KeyError:
                abort(400)
                return [[p.hsh, p.width, p.height] for p in self.search(search_filter, sort_by)]


    def search(self, search_filter, sort_by):
        select = "Photos.Hash, Path, Mime, Width, Height, Timestamp FROM Photos INNER JOIN Files ON Photos.Hash=Files.HASH"
        where = search_filter.get_clause()
        order_by = sort_by.get_clause()

        if order_by is not None:
            query = f"SELECT {select} WHERE ({where}) ORDER BY {order_by};"
        else:
            query = f"SELECT {select} WHERE ({where});"
        with self.fo.con() as c:
            print(query)
            c.execute(query)
            r = c.fetchall()

        photos = []
        for (hsh, path, mime, width, height, timestamp) in r:
            thumb_path, thumb_mime = self.fo.cas.thumb_path_mime(hsh)
            photos.append(CAS.Photo(hsh, path, mime, thumb_path, thumb_mime, width, height, timestamp))

        if search_filter.callback is not None:
            photos = [p for p in photos if search_filter.callback(p)]
        if sort_by.callback is not None:
            photos.sort(key=sort_by.callback)
        return photos
            
        
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
