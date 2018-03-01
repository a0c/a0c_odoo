from openerp import api, models


class ir_model_fields(models.Model):
    _inherit = 'ir.model.fields'

    @api.multi
    def action_view_objects_with_product(self):
        product = self._context.get('product')
        if not product:
            return
        recs = self.get_objects_with_product(product)
        return recs.action_view_tree(ctx_upd={'active_test': False})

    def get_objects_with_product(self, product):
        return self.env[self.model].with_context(active_test=False).search([(self.name, '=', product)], order='id desc')
