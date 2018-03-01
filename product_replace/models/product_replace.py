from openerp import api, fields, models, SUPERUSER_ID
from openerp.exceptions import Warning

from openerp.addons.auditlog_decorator.models.auditlog import audit
from openerp.addons.sql_utils import ids_sql, str_sql, drop_duplicates, fetchall, fetchone, fetchallsingle

NO_DUPLICATES = 'Could not suggest any Duplicate Products, sorry. ' \
                       'You can still manually select products you want to replace.'

NO_OTHER_DUPLICATES = 'No other Duplicate Products could be found for suggesting, sorry. ' \
                       'You can still manually select products you want to replace.'


def non_stored_related(field):
    return field.type in ('many2many', 'many2one') and not field.store


EMPTY_DICT = {}


class product_replace(models.TransientModel):
    _name = 'product.replace'

    state = fields.Selection([('draft', 'Draft'), ('replaced', 'Replaced')], default='draft')
    unknown_fields = fields.Many2many('ir.model.fields', 'product_replace_field_rel', 'wiz_id', 'field_id', ordered=1)
    product_old = fields.Many2one('product.product', 'Old Product', help='Product to replace')
    product_new = fields.Many2one('product.product', 'New Product', help='Replacement Product')
    product_old_next = fields.Many2one('product.product', 'Next Old Product')
    product_new_next = fields.Many2one('product.product', 'Next New Product')
    product_old_id = fields.Integer(compute='_product_old_id', help="ID of Old Product")
    product_new_cands = fields.Html(readonly=1, help='Up to 3 suggestions for New Product with similar Name/Code')
    info = fields.Char(readonly=1)

    # products
    pl_items = fields.Many2many('product.pricelist.item', 'product_replace_product_pricelist_item_rel', 'wiz_id', 'item_id', ordered=1)
    attr_vals = fields.Many2many('product.attribute.value', 'product_replace_product_attribute_value_rel', 'wiz_id', 'val_id', ordered=1)
    procs = fields.Many2many('procurement.order', 'product_replace_procurement_order_rel', 'wiz_id', 'proc_id', ordered=1)

    # templates
    pl_items_tmpl = fields.Many2many('product.pricelist.item', 'product_replace_product_pricelist_item_tmpl_rel', 'wiz_id', 'item_id', ordered=1)
    price_hist = fields.Many2many('product.price.history', 'product_replace_product_price_hist_rel', 'wiz_id', 'hist_id', ordered=1)
    attr_price = fields.Many2many('product.attribute.price', 'product_replace_product_attr_price_rel', 'wiz_id', 'price_id', ordered=1)
    attr_line = fields.Many2many('product.attribute.line', 'product_replace_product_attr_line_rel', 'wiz_id', 'line_id', ordered=1)
    packaging = fields.Many2many('product.packaging', 'product_replace_product_packaging_rel', 'wiz_id', 'packaging_id', ordered=1)
    supplierinfo = fields.Many2many('product.supplierinfo', 'product_replace_product_supplierinfo_rel', 'wiz_id', 'supplinfo_id', ordered=1)

    @api.model
    def default_get(self, fields_list):
        res = super(product_replace, self).default_get(fields_list)
        dupl_id, orig_id = self.next_duplicates()
        if dupl_id:
            res['product_old_next'] = dupl_id
            res['product_new_next'] = orig_id
        else:
            res['info'] = NO_DUPLICATES
        return res

    def _product_old_id(self):
        for x in self:
            x.product_old_id = x.product_old.id

    @api.onchange('product_old')
    def onchange_product_old(self):
        # update unknown_fields
        if self.product_old:
            supported_fields = self._supported_fields()
            product_old_vals = self._product_old_vals()
            res = self.env['ir.model.fields']
            for field in res.search([('relation', 'in', ('product.product', 'product.template')),
                                     ('id', 'not in', supported_fields.ids)], order='id desc'):
                model = self.env[field.model]
                # skip removed fields still present in db
                if field.name not in model._fields:
                    continue
                field_8 = model._fields[field.name]
                # only accept stored fields of regular models:
                # skip Transient Models, SQL Views, non-stored related fields (API 8/7)
                if model.is_transient() or not model._auto or non_stored_related(field_8):
                    continue
                # skip fields that were never written product_old to
                if not model.search([(field.name, '=', product_old_vals[field.relation])], limit=1):
                    continue
                res += field
            self.unknown_fields = res
        else:
            self.unknown_fields = False
        # collect usages
        self.collect()
        # set product_new & product_new_cands
        if not self._context.get('keep_cands'):
            first_cand, product_new_cands = self._find_similar_name_or_code([self.product_old.name_template, self.product_old.default_code], self.product_old.id)
            self.product_new_cands = product_new_cands
            if not self._context.get('keep_new'):
                self.product_new = first_cand or self.product_old
                self.highlight_candidate()

    def _product_old_vals(self):
        return {'product.product': self.product_old.id, 'product.template': self.product_old.product_tmpl_id.id}

    def onchange_product_old_keep_new(self, keep_cands=False):
        self.with_context(keep_new=1, keep_cands=keep_cands).onchange_product_old()
        self.highlight_candidate()

    @api.onchange('product_new')
    def highlight_candidate(self):
        if self.product_new_cands:
            self.product_new_cands = self.product_new_cands.replace(' style="color: green"', '').\
                replace(u' <i class="fa fa-check" aria-hidden="true" title="Matches current New Product">\xa0</i>', '')
        if self.product_new and self.product_new_cands:
            name = self.product_new.name_get()[0][1]
            if name in self.product_new_cands:
                self.product_new_cands = self.product_new_cands.replace(
                    name, '<span style="color: green">%s <i class="fa fa-check" aria-hidden="true" title="Matches current New Product">&nbsp;</i></span>' % name)

    @api.multi
    def collect(self):
        self._collect('pl_items')
        self._collect('attr_vals', 'product_ids')
        self._collect('procs')
        self._collect_tmpl('pl_items_tmpl')
        self._collect_tmpl('price_hist', 'product_template_id')
        self._collect_tmpl('attr_price')
        self._collect_tmpl('attr_line')
        self._collect_tmpl('packaging')
        self._collect_tmpl('supplierinfo')

    def _collect(self, field_name, field='product_id'):
        self.__collect(field_name, field, self.product_old.id)

    def _collect_tmpl(self, field_name, field='product_tmpl_id'):
        self.__collect(field_name, field, self.product_old.product_tmpl_id.id)

    def __collect(self, field_name, field, value):
        recs = getattr(self, field_name)
        res = self.product_old and recs.search([(field, '=', value)], order='id desc').ids or []
        setattr(self, field_name, [(6, 0, res)])

    @api.multi
    @audit
    def replace(self):
        """ update in SQL to avoid onchanges of ORM """
        self.ensure_both_products()
        self.ensure_products_differ()
        if self._uid != SUPERUSER_ID:
            raise Warning("Only Administrator is allowed to replace products. Even if allowed, normal users wouldn't "
                          "be able to see many objects because of Record Rules limitations (multi-company objects, "
                          "limitations by Warehouse, etc).")
        self.state = 'replaced'
        # update pl_items' NAMES first
        self._onchange_records(self.pl_items, 'product_id_change', (self.product_old.id,), args_new=(self.product_new.id,))
        self._update_records(self.pl_items)
        self._update_records_rel(self.attr_vals, 'product_attribute_value_product_product_rel', 'prod_id', 'product_ids')
        self._update_records(self.procs)
        self._update_records_tmpl(self.pl_items_tmpl)
        self._update_records_tmpl(self.price_hist, 'product_template_id')
        self._update_records_tmpl(self.attr_price)
        self._update_records_tmpl(self.attr_line)
        self._update_records_tmpl(self.packaging)
        self._update_records_tmpl(self.supplierinfo)
        self._invalidate_cache(self.supplierinfo, ['product_uom'])
        if self._context.get('replace_all'):
            product_old_vals = self._product_old_vals()
            for field in self.unknown_fields:
                field_8 = self.env[field.model]._fields[field.name]
                recs = field.get_objects_with_product(product_old_vals[field.relation])
                if field_8.type == 'many2one':
                    if field.relation == 'product.product':
                        self._update_records(recs, field.name)
                    elif field.relation == 'product.template':
                        self._update_records_tmpl(recs, field.name)
                elif field_8.type == 'many2many':
                    if field.relation == 'product.product':
                        self._update_records_rel(recs, field_8.relation, field_8.column2, field.name)
                    elif field.relation == 'product.template':
                        self._update_records_tmpl_rel(recs, field_8.relation, field_8.column2, field.name)

    def ensure_both_products(self):
        if not (self.product_old and self.product_new):
            raise Warning("Old Product and New Product must be both specified")

    def ensure_products_differ(self):
        if self.product_old == self.product_new:
            raise Warning("Old Product and New Product must be different")

    def ensure_old_product(self):
        if not self.product_old:
            raise Warning("Old Product must be specified")

    def _update_records(self, recs, field='product_id', field_value=None):
        self.__update_records(recs, field, self.product_new.id, field_value)

    def _update_records_tmpl(self, recs, field='product_tmpl_id', field_value=None):
        self.__update_records(recs, field, self.product_new.product_tmpl_id.id, field_value)

    def __update_records(self, recs, field, value, field_value):
        if not recs: return
        if field_value is None:
            field_value = '%s=%s' % (field, value)
        cmd = "UPDATE %s SET %s WHERE id in %s" % (recs._table, field_value, ids_sql(recs.ids))
        self._cr.execute(cmd)
        self._context['audit_msgs'].append(cmd)
        recs.invalidate_cache([field_value[:field_value.index('=')]], recs.ids)

    def _update_records_rel(self, recs, table, field, fname):
        self.__update_records_rel(recs, table, field, fname, self.product_old.id, self.product_new.id)

    def _update_records_tmpl_rel(self, recs, table, field, fname):
        self.__update_records_rel(recs, table, field, fname, self.product_old.product_tmpl_id.id, self.product_new.product_tmpl_id.id)

    def __update_records_rel(self, recs, table, field, fname, val_old, val_new):
        if not recs: return
        vals = dict(rel=table, f=field, old=val_old, new=val_new)
        cmd = "UPDATE {rel} SET {f}={new} WHERE {f}={old}".format(**vals)
        self._cr.execute(cmd)
        self._context['audit_msgs'].append(cmd)
        recs.invalidate_cache([fname], recs.ids)

    def _onchange_records(self, records, onchange, args_old=tuple(), kwargs_old=None, args_new=tuple(), kwargs_new=None):
        """ calls onchange on records with *static* args/kwargs. static args allow bulk update.
            use _onchange_each_record() for dynamic args that depend on each record """
        if kwargs_old is None: kwargs_old = {}
        if kwargs_new is None: kwargs_new = {}
        for user_lang, recs in records.group_by('create_uid.lang'):
            recs_ctx = recs.with_context(lang=user_lang or 'en_US')
            old_onchange = getattr(recs_ctx, onchange)(*args_old, **kwargs_old)
            new_onchange = getattr(recs_ctx, onchange)(*args_new, **kwargs_new)
            old_name = (old_onchange or EMPTY_DICT).get('value', EMPTY_DICT).get('name')
            new_name = (new_onchange or EMPTY_DICT).get('value', EMPTY_DICT).get('name')
            if new_name and new_name != old_name:
                # skip recs with non-default custom-set names
                recs_safe_to_rename = recs.filtered(lambda x: x.name == old_name)
                self._update_records(recs_safe_to_rename, field_value="name='%s'" % str_sql(new_name))

    def _onchange_each_record(self, records, old_onchange_fnc, new_onchange_fnc):
        """ calls onchange on records with *dynamic* args/kwargs that depend on each record """
        field_value_by_recs = {}
        for user_lang, recs in records.group_by('create_uid.lang'):
            recs_ctx = recs.with_context(lang=user_lang or 'en_US')
            for rec in recs_ctx:
                old_name = (old_onchange_fnc(rec) or EMPTY_DICT).get('value', EMPTY_DICT).get('name')
                new_name = (new_onchange_fnc(rec) or EMPTY_DICT).get('value', EMPTY_DICT).get('name')
                if new_name and new_name != old_name:
                    # skip recs with non-default custom-set names
                    recs_safe_to_rename = rec.filtered(lambda x: x.name == old_name)
                    field_value = "name='%s'" % str_sql(new_name)
                    if field_value in field_value_by_recs:
                        field_value_by_recs[field_value] += recs_safe_to_rename
                    else:
                        field_value_by_recs[field_value] = recs_safe_to_rename
        for field_value, recs in field_value_by_recs.iteritems():
            self._update_records(recs, field_value=field_value)

    def _update_records_transl(self, records, field_value_tmpl="name='%s'", value_field='name'):
        for user_lang, recs in records.group_by('create_uid.lang'):
            value = self.product_new.with_context(lang=user_lang or 'en_US').mapped(value_field)[0]
            if isinstance(value, basestring):
                value = str_sql(value)
            self._update_records(recs, field_value=field_value_tmpl % value)

    def _invalidate_cache(self, recs, fields):
        recs.invalidate_cache(fields, recs.ids)

    def replace_audit(self):
        self.ensure_both_products()
        header = '%s replaced product <b>#%s %s</b> with <b>#%s %s</b>\n' \
                 'and product template <b>#%s %s</b> with <b>#%s %s</b>:' % \
                 (self.env.user.name,
                  self.product_old.id, self.product_old.name_get()[0][1],
                  self.product_new.id, self.product_new.name_get()[0][1],
                  self.product_old.product_tmpl_id.id, self.product_old.product_tmpl_id.name_get()[0][1],
                  self.product_new.product_tmpl_id.id, self.product_new.product_tmpl_id.name_get()[0][1])
        messages = [header]
        for recs, title in self._replace_audit_recs():
            if recs:
                messages.append('<b>%s</b>: %s' % (title, recs.ids))
        return '', '\n'.join(messages)

    def _replace_audit_recs(self):
        res = [(self.pl_items, 'Pricelist Items'), (self.attr_vals, 'product.attribute.value'), (self.procs, 'Procurements'),
               (self.pl_items_tmpl, 'Pricelist Items [Template]'), (self.price_hist, 'product.price.history [Template]'),
               (self.attr_price, 'product.attribute.price [Template]'), (self.attr_line, 'product.attribute.line [Template]'),
               (self.packaging, 'Packaging [Template]'), (self.supplierinfo, 'Information about a product supplier [Template]')]
        if self._context.get('replace_all'):
            product_old_vals = self._product_old_vals()
            prefixes = {'product.product': '', 'product.template': ' [Template]'}
            for field in self.unknown_fields:
                recs = field.get_objects_with_product(product_old_vals[field.relation])
                res.append((recs, field.model_id.name + prefixes[field.relation]))
        return res

    @api.multi
    @audit
    def delete(self):
        self.ensure_old_product()
        self.product_old.unlink()

    def delete_audit(self):
        self.ensure_old_product()
        messages = '%s deleted product <b>#%s %s</b>' % \
                   (self.env.user.name, self.product_old.id, self.product_old.name_get()[0][1])
        return '', messages

    @api.multi
    def suggest_next_duplicates(self):
        # use previously found duplicates
        self.product_old = self.product_old_next
        self.product_new = self.product_new_next
        self.onchange_product_old_keep_new()
        # find next duplicates
        dupl_id, orig_id = self.next_duplicates()
        self.product_old_next = dupl_id
        self.product_new_next = orig_id
        self.info = NO_OTHER_DUPLICATES if not dupl_id else False  # clear

    def next_duplicates(self, since_product=None):
        if since_product is None:
            since_product = self.product_old.id
        cmd = "SELECT id, default_code FROM product_product WHERE default_code = name_template %s ORDER BY id DESC" % \
              (since_product and 'AND id < %s' % since_product or '')  # '<' works together with 'ORDER BY id DESC'
        same_code_name = fetchall(self._cr, cmd)
        for dupl_id, default_code in same_code_name:
            cmd = "SELECT id FROM product_product WHERE name_template=%s and default_code!=name_template ORDER BY id LIMIT 1"
            orig_id = fetchone(self._cr, cmd, (default_code,))
            if orig_id:
                return dupl_id, orig_id[0]
        return False, False

    @api.multi
    def suggest_next_same_code_name(self):
        dupl_id, (first_cand, product_new_cands) = self.next_same_code_name_with_cands()
        self.product_old = dupl_id
        self.product_new = first_cand or dupl_id
        self.product_new_cands = product_new_cands
        self.onchange_product_old_keep_new(keep_cands=1)

    def next_same_code_name_with_cands(self):
        direction = self._context.get('direction', 'DESC')
        where = self.product_old and 'AND id %s %s' % (direction == 'DESC' and '<' or '>', self.product_old.id) or ''
        cmd = "SELECT id, default_code FROM product_product WHERE default_code = name_template %s ORDER BY id %s LIMIT 1" % (where, direction)
        same_code_name = fetchall(self._cr, cmd)
        for dupl_id, default_code in same_code_name:
            return dupl_id, self._find_similar_name_or_code([default_code], dupl_id)
        return False, (False, False)

    def _find_similar_name_or_code(self, names, skip_id):
        """ :return: tuple(first_cand, product_new_cands) """
        if not skip_id: return False, False
        similar = self._find_similar_3x(names, skip_id)
        products = self.env['product.product'].browse(similar)
        product_new_cands = '<br>'.join(name for id, name in products.name_get())
        if product_new_cands:
            return similar[0], product_new_cands
        return False, 'No suggestions for New Product, sorry. Try typing parts of Old Product\'s ' \
                      'name/code or even dropping some characters from code.'

    def _find_similar_3x(self, names, skip_id):
        """ :return: at most 3x matching product_ids """
        similar = "SELECT id FROM product_product WHERE %s ilike '%%%s%%' and id not in %s ORDER BY id LIMIT 3"
        res = []
        for name in drop_duplicates(names):
            for field in 'name_template', 'default_code':
                res += fetchallsingle(self._cr, similar % (field, str_sql(name), ids_sql([skip_id] + res)))
                if len(res) >= 3:
                    return res[:3]
        return res[:3]

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        """ force active_test = False to also show inactive objects where to replace product """
        return super(product_replace, self.with_context(active_test=False)).read(fields=fields, load=load)

    @api.model
    def _supported_fields(self):
        """ don't replace these 3x base fields + mark 9x supported fields """
        return self._get_field('product.template', 'product_variant_ids') | \
               self._get_field('product.product', 'product_variant_ids') | \
               self._get_field_tmpl('product.product') | \
               self._get_field('product.pricelist.item') | \
               self._get_field('product.attribute.value', 'product_ids') | \
               self._get_field('procurement.order') | \
               self._get_field_tmpl('product.pricelist.item') | \
               self._get_field_tmpl('product.price.history', 'product_template_id') | \
               self._get_field_tmpl('product.attribute.price') | \
               self._get_field_tmpl('product.attribute.line') | \
               self._get_field_tmpl('product.packaging') | \
               self._get_field_tmpl('product.supplierinfo')

    def _get_field(self, model, field='product_id'):
        return self.env['ir.model.fields'].search([('model', '=', model), ('name', '=', field), ('relation', '=', 'product.product')], limit=1)

    def _get_field_tmpl(self, model, field='product_tmpl_id'):
        return self.env['ir.model.fields'].search([('model', '=', model), ('name', '=', field), ('relation', '=', 'product.template')], limit=1)
