from collections import namedtuple
from .formulaic import formulaic, field, OneOfField, Option, SubmitField
from .component import Component


SearchFilter = namedtuple('SearchFilter', ['name', 'description', 'fields', 'sql', 'callback'], defaults=({}, None, None))


#SortBy = namedtuple('SortBy', ['name', 'description', 'fields', 'sql', 'sort_key'], defaults=({}, None, None))


class SortBy:
    def __init__(self):
        ...

    @staticmethod
    def description():
        raise NotImplementedError


class Search(Component):
    def __init__(self, fo):
        self.fo = fo

    @property
    def sort_bys(self):
        l = []
        for component in self.fo.components:
            if hasattr(component, 'get_sort_bys'):
                for sort_by in component.get_sort_bys():
                    l.append(formulaic(sort_by))
        return l

    @property
    def search_filters(self):
        l = []
        for component in self.fo.components:
            if hasattr(component, 'get_search_filters'):
                for search_filter in component.get_search_filters():
                    l.append(formulaic(search_filter))
        return l

    def get_request_class(self):
        options = [Option(sb.__name__, sb.description(), sb) for sb in self.sort_bys]
        @field('sort_by', "Sort by", OneOfField(options))
        @field('submit', "Go!", SubmitField("/search"))
        class SearchRequest:
            def __init__(self, sort_by):
                self.sort_by = sort_by
        return SearchRequest


    def get_search_results(self, search_request):
        breakpoint()
        
        if sort_by is not None:
            breakpoint()
        
        if search_list == "all":
            result = self.cas.list_all_photos()
            editable = False
        else:
            with self.con(True) as c:
                c.execute("SELECT Photos.Hash, Width, Height FROM Albums INNER JOIN Photos on Albums.Hash=Photos.Hash WHERE Album=? ORDER BY Photos.Timestamp", (search_list,))
                result = c.fetchall()
                editable = True

        if sort_by is not None and sort_by.sort_key is not None:
            result.sort(key=lambda hwh: sort_by.sort_key(hwh[0]))
            
        return result, editable
