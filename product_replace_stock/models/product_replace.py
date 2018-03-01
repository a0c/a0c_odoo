from openerp import api, fields, models

from openerp.addons.auditlog_decorator.models.auditlog import audit


class product_replace(models.TransientModel):
    _inherit = 'product.replace'

    # products
    moves = fields.Many2many('stock.move', 'product_replace_stock_move_rel', 'wiz_id', 'move_id', ordered=1)
    pack_ops = fields.Many2many('stock.pack.operation', 'product_replace_stock_pack_op_rel', 'wiz_id', 'op_id', ordered=1)
    quants = fields.Many2many('stock.quant', 'product_replace_stock_quant_rel', 'wiz_id', 'quant_id', ordered=1)
    lots = fields.Many2many('stock.production.lot', 'product_replace_stock_production_lot_rel', 'wiz_id', 'lot_id', ordered=1)
    invs = fields.Many2many('stock.inventory', 'product_replace_stock_inventory_rel', 'wiz_id', 'inv_id', ordered=1)
    inv_lines = fields.Many2many('stock.inventory.line', 'product_replace_stock_inventory_line_rel', 'wiz_id', 'line_id', ordered=1)
    wh_orderpoints = fields.Many2many('stock.warehouse.orderpoint', 'product_replace_stock_wh_orderpoint_rel', 'wiz_id', 'orderpoint_id', ordered=1)

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

    @api.multi
    @audit
    def replace(self):
        super(product_replace, self.with_context(no_audit=1)).replace()

        # update lots first, as lots could fail-fast when duplicates found
        # todo: if this happens, find all usages of failed self.lots and replace them with existing duplicates
        self._update_records(self.lots)

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

        self._update_records(self.invs)

        self._update_records(self.inv_lines)
        self._update_records_transl(self.inv_lines, "product_name='%s'", 'name')
        self._update_records_transl(self.inv_lines, "product_code='%s'", 'default_code')

        self._update_records(self.wh_orderpoints)

    def _replace_audit_recs(self):
        res = super(product_replace, self)._replace_audit_recs()
        res.extend([(self.lots, 'S/N'), (self.moves, 'Stock Moves'), (self.pack_ops, 'Pack Operations'),
                    (self.quants, 'Quants'), (self.invs, 'Inventories'), (self.inv_lines, 'Inventory Lines'),
                    (self.wh_orderpoints, 'Minimum Inventory Rules')])
        return res

    def _supported_fields(self):
        res = super(product_replace, self)._supported_fields()
        for model in 'stock.move', 'stock.pack.operation', 'stock.quant', 'stock.production.lot', 'stock.inventory',\
                     'stock.inventory.line', 'stock.warehouse.orderpoint':
            res |= self._get_field(model)
        return res
