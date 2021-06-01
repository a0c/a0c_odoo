from openerp import api, fields, models

from openerp.addons.auditlog_decorator.models.auditlog import audit
from openerp.addons.sql_utils import ids_sql, fetchall

LOT_FIELDS_BY_WIZ_FIELD = {
    'moves': 'restrict_lot_id',
    'pack_ops': 'lot_id',
    'quants': 'lot_id',
    'lots': 'id',
    'invs': 'lot_id',
    'inv_lines': 'prod_lot_id',
}


class product_replace(models.TransientModel):
    _inherit = 'product.replace'

    lot = fields.Many2one('stock.production.lot', 'Serial Number', help="Filter Records by this Serial Number")

    # products
    moves = fields.Many2many('stock.move', 'product_replace_stock_move_rel', 'wiz_id', 'move_id', ordered=1)
    pack_ops = fields.Many2many('stock.pack.operation', 'product_replace_stock_pack_op_rel', 'wiz_id', 'op_id', ordered=1)
    quants = fields.Many2many('stock.quant', 'product_replace_stock_quant_rel', 'wiz_id', 'quant_id', ordered=1)
    lots = fields.Many2many('stock.production.lot', 'product_replace_stock_production_lot_rel', 'wiz_id', 'lot_id', ordered=1)
    invs = fields.Many2many('stock.inventory', 'product_replace_stock_inventory_rel', 'wiz_id', 'inv_id', ordered=1)
    inv_lines = fields.Many2many('stock.inventory.line', 'product_replace_stock_inventory_line_rel', 'wiz_id', 'line_id', ordered=1)
    wh_orderpoints = fields.Many2many('stock.warehouse.orderpoint', 'product_replace_stock_wh_orderpoint_rel', 'wiz_id', 'orderpoint_id', ordered=1)

    @api.onchange('lot')
    def onchange_lot(self):
        """ Lot is currently used for analysis only and thus disables Replace buttons. Here we force-clear
            all recs loaded for analysis to prevent Replacing product just in these recs instead of in all recs. """
        if not self.lot:
            self.product_old = False
            self.product_new = False
        else:
            self.product_old = self.lot.product_id  # auto-load Old Product

    @api.multi
    def collect(self):
        super(product_replace, self).collect()
        self._collect('moves')
        self._collect('pack_ops')
        self._collect('quants')
        self._collect('lots')
        self._collect('invs')
        self._collect('inv_lines')
        self._collect('wh_orderpoints')

    def search_recs(self, field_name, field, value):
        if self.lot and field_name not in LOT_FIELDS_BY_WIZ_FIELD:
            return []  # hide fields w/o lot on them
        return super(product_replace, self).search_recs(field_name, field, value)

    def args_recs(self, recs, field_name, field, value):
        """ override to only return recs related to lot selected """
        res = super(product_replace, self).args_recs(recs, field_name, field, value)
        if self.lot and field_name in LOT_FIELDS_BY_WIZ_FIELD:
            res.append((LOT_FIELDS_BY_WIZ_FIELD[field_name], '=', self.lot.id))
        return res

    @api.multi
    @audit
    def replace(self):
        super(product_replace, self.with_context(no_audit=1)).replace()
        self = self.sudo()

        # update moves' NAMES first - otherwise moves' product_id will be overwritten with product_new
        # skip moves with names like 'INV: Initial Inventory'
        old_onchange_fnc = lambda x: x.onchange_product_id(prod_id=self.product_old.id, loc_id=x.location_id.id,
                                                           loc_dest_id=x.location_dest_id.id, partner_id=x.partner_id.id)
        new_onchange_fnc = lambda x: x.onchange_product_id(prod_id=self.product_new.id, loc_id=x.location_id.id,
                                                           loc_dest_id=x.location_dest_id.id, partner_id=x.partner_id.id)
        self._onchange_each_record(self.moves, old_onchange_fnc, new_onchange_fnc)
        self._update_records(self.moves)
        self._invalidate_cache(self.moves, ['product_tmpl_id', 'remaining_qty', 'availability'])

        self._update_records(self.pack_ops)

        self._update_records(self.quants)
        self._invalidate_cache(self.quants, ['name', 'inventory_value'])

        self._replace_lots()

        self._update_records(self.invs)

        self._update_records(self.inv_lines)
        self._update_records_transl(self.inv_lines, "product_name='%s'", 'name')
        self._update_records_transl(self.inv_lines, "product_code='%s'", 'default_code')

        self._update_records(self.wh_orderpoints)

    def _replace_audit_recs(self):
        res = super(product_replace, self)._replace_audit_recs()
        res.extend([(self.moves, 'Stock Moves'), (self.pack_ops, 'Pack Operations'), (self.quants, 'Quants'),
                    (self.lots, 'S/N'), (self.invs, 'Inventories'), (self.inv_lines, 'Inventory Lines'),
                    (self.wh_orderpoints, 'Minimum Inventory Rules')])
        return res

    def _supported_fields(self):
        res = super(product_replace, self)._supported_fields()
        for model in 'stock.move', 'stock.pack.operation', 'stock.quant', 'stock.production.lot', 'stock.inventory',\
                     'stock.inventory.line', 'stock.warehouse.orderpoint':
            res |= self._get_field(model)
        return res

    def _replace_lots(self):
        """ if lots fail to update because duplicates with product_new found -
            find all usages of failed self.lots and replace them with existing duplicates """
        unique_lots = self.lots.browse()
        for lot in self.lots:
            existing = self._find_existing_lot(lot)
            if existing:
                usages_of_old_lot = self._find_fields({'stock.production.lot': lot.id}, with_usages=True)
                for field, usages_of_old in usages_of_old_lot.iteritems():
                    self._update_records(usages_of_old, field_value='%s=%s' % (field.name, existing.id))
                self._context['audit_msgs'].append('DELETE FROM %s WHERE id in %s' % (lot._table, ids_sql(lot.ids)))
                lot.unlink()
            else:
                unique_lots |= lot
        self._update_records(unique_lots)

    def _find_existing_lot(self, lot):
        """ can be overridden if default sql_constraint is changed """
        return lot.search([('name', '=', lot.name), ('product_id', '=', self.product_new.id),
                           ('ref', '=', self.product_new.ref)], limit=1)


class stock_production_lot(models.Model):
    _inherit = 'stock.production.lot'

    products_with_duplicate = fields.Char('Products with Duplicate S/N', compute='_products_with_duplicate')

    def _products_with_duplicate(self):
        if not self._context.get('allow_compute_products_with_duplicate'): return
        cmd = """
SELECT l.id, STRING_AGG(CONCAT('[', l.default_code, '] ', l.name_template), '\n')
FROM stock_production_lot lot,
     LATERAL (
         SELECT lot.id, p.default_code, p.name_template
         FROM stock_production_lot lot_inner
             JOIN product_product p on lot_inner.product_id = p.id
         WHERE lot_inner.name = lot.name AND lot_inner.id != lot.id -- lateral reference
         ORDER BY p.default_code, p.name_template
         ) l
WHERE lot.id in %s
GROUP BY l.id;
"""
        products_with_duplicate = {k: v for k, v in fetchall(self._cr, cmd, (tuple(self.ids),))}
        for x in self:
            x.products_with_duplicate = products_with_duplicate.get(x.id)
