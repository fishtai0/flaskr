from flask import request, abort
from playhouse.flask_utils import PaginatedQuery


class Pagination(PaginatedQuery):
    """Subclass of :class:`PaginatedQuery` to perform pagination."""

    def __init__(self, query_or_model, per_page, page=None, **kwargs):
        """Init pagination for Peewee with SelectQuery or Model.

        Arguments:
        - `per_page`: int, number of objects per-page.
        - `page`: int, current page number (1 indexed). if None,
                  try to get it from the `page_var` argument.
        """
        super(Pagination, self).__init__(query_or_model, per_page, **kwargs)
        self._page = page

    @property
    def total(self):
        """Total number of items matching the query."""
        return self.query.count()

    @property
    def items(self):
        """Items for the current page."""
        return self.get_object_list()

    @property
    def page(self):
        """Current page number (1 indexed)."""
        if self._page is None:
            try:
                page = int(request.args.get(self.page_var, 1))
            except (TypeError, ValueError):
                if self.check_bounds:
                    abort(404)
                page = 1
            return page
        return self._page

    @property
    def pages(self):
        """The total number of pages."""
        if self.paginate_by == 0:
            pages = 0
        else:
            pages = self.get_page_count()
        return pages

    def prev(self, check_bounds=False):
        """Returns a :class:`Pagination` object for the previous page."""
        assert self.query is not None, 'a SelectQuery object is required ' \
            'for this method to work'
        return self.__class__(self.query,
                              self.page - 1, self.paginate_by, check_bounds)

    @property
    def prev_num(self):
        """Number of the previous page."""
        if not self.has_prev:
            return None
        return self.page - 1

    @property
    def has_prev(self):
        """True if a previous page exists"""
        return self.page > 1

    def next(self, check_bounds=False):
        """Returns a :class:`Pagination` object for the next page."""
        assert self.query is not None, 'a SelectQuery object is required ' \
            'for this method to work'
        return self.__class__(self.query,
                              self.page + 1, self.paginate_by, check_bounds)

    @property
    def has_next(self):
        """True if a next page exists."""
        return self.page < self.pages

    @property
    def next_num(self):
        """Number of the next page"""
        if not self.has_next:
            return None
        return self.page + 1

    def iter_pages(self, left_edge=2, left_current=2,
                   right_current=5, right_edge=2):
        """Iterates over the page numbers in the pagination.  The four
        parameters control the thresholds how many numbers should be produced
        from the sides.  Skipped page numbers are represented as `None`.
        This is how you could render such a pagination in the templates:

        .. sourcecode:: html+jinja

            {% macro render_pagination(pagination, endpoint) %}
              <div class=pagination>
              {%- for page in pagination.iter_pages() %}
                {% if page %}
                  {% if page != pagination.page %}
                    <a href="{{ url_for(endpoint, page=page) }}">{{ page }}</a>
                  {% else %}
                    <strong>{{ page }}</strong>
                  {% endif %}
                {% else %}
                  <span class=ellipsis>…</span>
                {% endif %}
              {%- endfor %}
              </div>
            {% endmacro %}
        """
        last = 0
        for num in range(1, self.pages + 1):
            if num <= left_edge or \
               (num > self.page - left_current - 1 and
                num < self.page + right_current) or \
                    num > self.pages - right_edge:
                if last + 1 != num:
                    yield None
                yield num
                last = num
