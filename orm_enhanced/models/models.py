from itertools import chain
from openerp import api
from openerp.osv.fields import _symbol_set_float
from openerp.osv.orm import BaseModel


def group_by(self, key, as_dict=False, ensure_keys=()):
    res = {}
    for k in ensure_keys: res[k] = []
    for x in self:
        by = x.mapped(key)
        res.setdefault(by[0] if by else by, []).append(x.id)
    for k in res:
        res[k] = self.browse(res[k])
    return res if as_dict else res.iteritems()

BaseModel.group_by = group_by


def partition_by(self, key, ensure_keys=()):
    grouped = self.group_by(key, as_dict=True, ensure_keys=ensure_keys).items()
    grouped.sort(key=lambda x: x[0])
    return [x[1] for x in grouped]

BaseModel.partition_by = partition_by


# PERFORMANCE methods

def firsts(self, key):
    """ returns *first* elements of the key-field of recs """
    ids = list(chain(*(x[key].ids[:1] for x in self)))
    recs = self.env[self._fields[key].comodel_name].browse(ids)
    return recs

BaseModel.firsts = firsts


def no_prefetch(self, fields=None):
    """ only prefetch `fields` for the *current* records (self).
        avoids prefetching `fields` for *all* records _in_cache_without `fields` """
    prefetch_ids = self._context.get('prefetch_ids', {})
    if fields is None:
        prefetch_ids[self._name] = set(self.ids)
    else:
        for f in fields:
            prefetch_ids['%s.%s' % (self._name, f)] = set(self.ids)
    return self.with_context(prefetch_ids=prefetch_ids)

BaseModel.no_prefetch = no_prefetch


def no_prefetch_field(self, key):
    field_recs = self.mapped(key).no_prefetch()
    return self.with_context(field_recs._context)

BaseModel.no_prefetch_field = no_prefetch_field


@api.model
def _in_cache_without(self, field):
    """ Make sure ``self`` is present in cache (for prefetching), and return
        the records of model ``self`` in cache that have no value for ``field``
        (:class:`Field` instance).
    """
    env = self.env
    prefetch_ids = env.prefetch[self._name]
    prefetch_ids.update(self._ids)
    ids = filter(None, prefetch_ids - set(env.cache[field]))
    ids = self._apply_prefetch_ids_in_context(ids, field)
    return self.browse(ids)

def _apply_prefetch_ids_in_context(self, ids, field):
    if self.env.context.get('prefetch_ids'):
        prefetch_ids = self.env.context['prefetch_ids'].get(str(field), self.env.context['prefetch_ids'].get(self._name))
        if prefetch_ids:
            ids = [x for x in ids if x in prefetch_ids]
    if hasattr(self, '_no_prefetch_fields'):
        if field.name in self._no_prefetch_fields:
            ids = [x for x in ids if x in self.ids]
    return ids

BaseModel._in_cache_without = _in_cache_without
BaseModel._apply_prefetch_ids_in_context = _apply_prefetch_ids_in_context

# PERFORMANCE methods


def _force_float_fields_precisions(self, cr):
    """ force requested precisions (digits) onto float fields
        Example:    DIGITS = (16, 3)

                    class project(models.Model):
                        _float_precisions = {DIGITS: ['planned_hours', 'effective_hours', 'total_hours']}
    """
    if hasattr(self, '_float_precisions') and isinstance(self._float_precisions, dict):
        for digits, fields in self._float_precisions.iteritems():
            for field in fields:
                # patch self._columns
                column = self._columns[field]
                column._digits = digits
                column._symbol_f = lambda x: _symbol_set_float(column, x)  # update lambda with a new column closure
                column._symbol_set = (column._symbol_c, column._symbol_f)  # update tuple with a new lambda
                # patch self._fields in case digits already defined on a field.float()
                field = self._fields[field]
                field._column_digits = field._description_digits = field._digits = field._related__digits = field.digits = digits

def _register_hook(self, cr):
    """ stuff to do right after the registry is built """
    _force_float_fields_precisions(self, cr)

BaseModel._register_hook = _register_hook
