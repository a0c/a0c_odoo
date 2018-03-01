from openerp.osv.orm import BaseModel


def group_by(self, key):
    res = {}
    for x in self:
        by = x.mapped(key)
        res.setdefault(by and by[0] or by, []).append(x.id)
    for k in res:
        res[k] = self.browse(res[k])
    return res.iteritems()

BaseModel.group_by = group_by
