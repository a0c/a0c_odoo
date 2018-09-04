from itertools import chain
from openerp import api
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

def firsts(self, key, fields):
    """ only prefetch `fields` of the *first* element of the key-field of recs.
        avoids prefetching `fields` for *all* elements of the key-field of recs. """
    field_model = self._fields[key].comodel_name
    ids = list(chain(*(x[key].ids[:1] for x in self)))
    recs = self.env[field_model].browse(ids)
    only_prefetch = recs._context.get('only_prefetch', {})
    for f in fields:
        only_prefetch['%s.%s' % (field_model, f)] = set(ids)
    return recs.with_context(only_prefetch=only_prefetch)

BaseModel.firsts = firsts


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
    if env.context.get('only_prefetch'):
        only_prefetch = env.context['only_prefetch'].get(str(field))
        if only_prefetch:
            ids = [x for x in ids if x in only_prefetch]
    return self.browse(ids)

BaseModel._in_cache_without = _in_cache_without

# PERFORMANCE methods
