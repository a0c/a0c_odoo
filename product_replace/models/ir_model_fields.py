from openerp import api, models


class ir_model_fields(models.Model):
    _inherit = 'ir.model.fields'

    @api.multi
    def action_view_recs_with_value(self):
        value = self._context.get('field_value')
        if not value:
            return
        recs = self.recs_with_value(value)
        return recs.with_context(allow_empty=1).action_view_tree(ctx_upd={'active_test': False})

    def recs_with_value(self, value, limit=None):
        return self.env[self.model].with_context(active_test=False).search([(self.name, '=', value)], limit=limit, order='id desc')
