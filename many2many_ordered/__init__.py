from openerp.models import BaseModel, _schema, except_orm
from openerp.osv.fields import many2many

from openerp.addons.sql_utils import fetchallsingle


def _m2m_raise_or_create_relation(self, cr, f):
    """ Create the table for the relation if necessary.
    Return ``True`` if the relation had to be created.

    To support ordering, we create ``id`` column as SERIAL PRIMARY KEY.
    Thus, to return items in the order they were added we just ordered by id.
    SERIAL saves us from having to manually handle the sequence, while
    PRIMARY KEY is indexed, thus allows quick search, especially with LIMIT n.
    """
    m2m_tbl, col1, col2 = f._sql_names(self)
    col_id, pkey = ('id SERIAL NOT NULL, ', ' PRIMARY KEY(id),') if f._args.get('ordered') else ('', '')
    # do not create relations for custom fields as they do not belong to a module
    # they will be automatically removed when dropping the corresponding ir.model.field
    # table name for custom relation all starts with x_, see __init__
    if not m2m_tbl.startswith('x_'):
        self._save_relation_table(cr, m2m_tbl)
    cr.execute("SELECT relname FROM pg_class WHERE relkind IN ('r','v') AND relname=%s", (m2m_tbl,))
    if not cr.dictfetchall():
        if f._obj not in self.pool:
            raise except_orm('Programming Error', 'Many2Many destination model does not exist: `%s`' % (f._obj,))
        dest_model = self.pool[f._obj]
        ref = dest_model._table
        cr.execute('CREATE TABLE "%s" (%s"%s" INTEGER NOT NULL, "%s" INTEGER NOT NULL,%s UNIQUE("%s","%s"))' %
                   (m2m_tbl, col_id, col1, col2, pkey, col1, col2))
        # create foreign key references with ondelete=cascade, unless the targets are SQL views
        cr.execute("SELECT relkind FROM pg_class WHERE relkind IN ('v') AND relname=%s", (ref,))
        if not cr.fetchall():
            self._m2o_add_foreign_key_unchecked(m2m_tbl, col2, dest_model, 'cascade')
        cr.execute("SELECT relkind FROM pg_class WHERE relkind IN ('v') AND relname=%s", (self._table,))
        if not cr.fetchall():
            self._m2o_add_foreign_key_unchecked(m2m_tbl, col1, self, 'cascade')

        cr.execute('CREATE INDEX "%s_%s_index" ON "%s" ("%s")' % (m2m_tbl, col1, m2m_tbl, col1))
        cr.execute('CREATE INDEX "%s_%s_index" ON "%s" ("%s")' % (m2m_tbl, col2, m2m_tbl, col2))
        cr.execute("COMMENT ON TABLE \"%s\" IS 'RELATION BETWEEN %s AND %s'" % (m2m_tbl, self._table, ref))
        cr.commit()
        _schema.debug("Create table '%s': m2m relation between '%s' and '%s'", m2m_tbl, self._table, ref)
        return True
    if f._args.get('ordered'):
        cr.execute("SELECT 1 FROM information_schema.columns WHERE table_name='%s' AND column_name='id'" % (m2m_tbl,))
        if not cr.fetchall():
            cr.execute('ALTER TABLE "%s" ADD COLUMN id SERIAL PRIMARY KEY' % (m2m_tbl,))

BaseModel._m2m_raise_or_create_relation = _m2m_raise_or_create_relation


_get_query_and_where_params_old = many2many._get_query_and_where_params

def _get_query_and_where_params(self, cr, model, ids, values, where_params):
    """ Extracted from ``get`` to facilitate fine-tuning of the generated
        query. """
    if self._args.get('ordered'):
        values['order_by'] = ' ORDER BY "%s".id ' % values['rel']
    return _get_query_and_where_params_old(self, cr, model, ids, values, where_params)

many2many._get_query_and_where_params = _get_query_and_where_params


def set(self, cr, model, id, name, values, user=None, context=None):
    if not context:
        context = {}
    if not values:
        return
    rel, id1, id2 = self._sql_names(model)
    obj = model.pool[self._obj]

    def link(ids):
        # beware of duplicates when inserting
        exc = ' EXCEPT (SELECT {id1}, {id2} FROM {rel} WHERE {id1}=%s)'
        ordered = self._args.get('ordered') and len(ids) > 1
        if ordered:
            # to preserve order, need to avoid EXCEPT (SELECT ...) inside INSERT stmt.
            # instead, filter out existing duplicates in a separate SELECT stmt.
            exc = ''
            excl = fetchallsingle(cr, 'SELECT {id2} FROM {rel} WHERE {id1}=%s'.format(rel=rel, id1=id1, id2=id2), (id,))
            ids = [i for i in ids if i not in excl]
        query = (""" INSERT INTO {rel} ({id1}, {id2})
                     (SELECT %s, unnest(%s))
                 """ + exc).format(rel=rel, id1=id1, id2=id2)
        for sub_ids in cr.split_for_in_conditions(ids):
            cr.execute(query, ordered and (id, list(sub_ids)) or (id, list(sub_ids), id))

    def unlink_all():
        # remove all records for which user has access rights
        clauses, params, tables = obj.pool.get('ir.rule').domain_get(cr, user, obj._name, context=context)
        cond = " AND ".join(clauses) if clauses else "1=1"
        query = """ DELETE FROM {rel} USING {tables}
                    WHERE {rel}.{id1}=%s AND {rel}.{id2}={table}.id AND {cond}
                """.format(rel=rel, id1=id1, id2=id2,
                           table=obj._table, tables=','.join(tables), cond=cond)
        cr.execute(query, [id] + params)

    for act in values:
        if not (isinstance(act, list) or isinstance(act, tuple)) or not act:
            continue
        if act[0] == 0:
            idnew = obj.create(cr, user, act[2], context=context)
            cr.execute('insert into '+rel+' ('+id1+','+id2+') values (%s,%s)', (id, idnew))
        elif act[0] == 1:
            obj.write(cr, user, [act[1]], act[2], context=context)
        elif act[0] == 2:
            obj.unlink(cr, user, [act[1]], context=context)
        elif act[0] == 3:
            cr.execute('delete from '+rel+' where ' + id1 + '=%s and '+ id2 + '=%s', (id, act[1]))
        elif act[0] == 4:
            link([act[1]])
        elif act[0] == 5:
            unlink_all()
        elif act[0] == 6:
            unlink_all()
            link(act[2])

many2many.set = set
