from openerp import api, fields, models

from openerp.addons.auditlog_decorator.models.auditlog import audit


class product_replace(models.TransientModel):
    _inherit = 'product.replace'

    # products
    analytic_lines = fields.Many2many('account.analytic.line', 'product_replace_acc_anal_line_rel', 'wiz_id', 'line_id', ordered=1)
    invoice_lines = fields.Many2many('account.invoice.line', 'product_replace_acc_inv_line_rel', 'wiz_id', 'line_id', ordered=1)
    move_lines = fields.Many2many('account.move.line', 'product_replace_acc_move_line_rel', 'wiz_id', 'line_id', ordered=1)

    @api.multi
    def collect(self):
        super(product_replace, self).collect()
        self._collect('analytic_lines')
        self._collect('invoice_lines')
        self._collect('move_lines')

    @api.multi
    @audit
    def replace(self):
        super(product_replace, self.with_context(no_audit=1)).replace()
        self = self.sudo()

        self._update_records(self.analytic_lines)

        # update lines' NAMES first - otherwise lines' product_id will be overwritten with product_new
        old_onchange_fnc = lambda x: x.product_id_change(self.product_old.id, x.uos_id.id, qty=x.quantity, name=x.name,
            type=x.invoice_id.type, partner_id=x.invoice_id.partner_id.id, fposition_id=x.invoice_id.fiscal_position.id,
            price_unit=x.price_unit, currency_id=x.invoice_id.currency_id.id, company_id=x.invoice_id.company_id.id)
        new_onchange_fnc = lambda x: x.product_id_change(self.product_new.id, x.uos_id.id, qty=x.quantity, name=x.name,
            type=x.invoice_id.type, partner_id=x.invoice_id.partner_id.id, fposition_id=x.invoice_id.fiscal_position.id,
            price_unit=x.price_unit, currency_id=x.invoice_id.currency_id.id, company_id=x.invoice_id.company_id.id)
        self._onchange_each_record(self.invoice_lines, old_onchange_fnc, new_onchange_fnc)
        self._update_records(self.invoice_lines)

        self._update_records(self.move_lines)

    def _replace_audit_recs(self):
        res = super(product_replace, self)._replace_audit_recs()
        res.extend([(self.analytic_lines, 'Analytic Lines'), (self.invoice_lines, 'Invoice Lines'),
                    (self.move_lines, 'Journal Items')])
        return res

    def _supported_fields(self):
        res = super(product_replace, self)._supported_fields()
        for model in 'account.analytic.line', 'account.invoice.line', 'account.move.line':
            res |= self._get_field(model)
        return res
