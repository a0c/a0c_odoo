from openerp import api, fields, models


class message_wizard(models.TransientModel):
    _name = 'message.wizard'
    _description = 'Message Wizard'
    _inherit = ['downloadable']

    message = fields.Html('Message', readonly=1)

    @api.multi
    def act_msg(self, title, msg_or_vals, form_xmlid=None, action_xmlid=None, ctx_upd=False):
        """ example: return self.env['message.wizard'].act_msg('Notifications Sent', msg) """
        if not isinstance(msg_or_vals, dict):
            msg_or_vals = {'message': msg_or_vals}
        form_xmlid = form_xmlid or 'orm_enhanced.view_message_wizard_form'
        act = self.create(msg_or_vals).action_view(form_xmlid, action_xmlid=action_xmlid, ctx_upd=ctx_upd)
        act.update(target='new', name=title)
        return act

    @api.multi
    def action_ok(self):
        """ close wizard """
        return {'type': 'ir.actions.act_window_close'}
