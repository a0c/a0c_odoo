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
