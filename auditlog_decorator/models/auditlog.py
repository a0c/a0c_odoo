import logging

from openerp import fields, models
from openerp.api import WRAPPED_ATTRS

logger = logging.getLogger('[AUDIT]')


class AuditlogLog(models.Model):
    _inherit = 'auditlog.log'
    _order = "create_date desc, id desc"

    message = fields.Text(readonly=1)


def audit(fnc):
    def get_audit_message(self, *args, **kw):
        msg_fnc = fnc.func_name + '_audit'
        if hasattr(self, msg_fnc):
            log_prefix, message = getattr(self, msg_fnc)(*args, **kw)
        else:
            log_prefix, message = ('', fnc.func_name)  # non-empty message, to hide Fields in log form view
            logger.warn('Audit message method \'%s()\' missing in %s', msg_fnc, self._name)
        return log_prefix, message

    def wrapper(self, *args, **kw):
        do_audit = self and not self._context.get('no_audit')
        if do_audit:
            rule_obj = self.env['auditlog.rule']
            if self._name not in rule_obj.pool._auditlog_model_cache:
                rule_obj.pool._auditlog_model_cache[self._name] = self.env['ir.model'].search([('model', '=', self._name)], limit=1).id
            log_prefix, message = get_audit_message(self, *args, **kw)
            rule_obj.sudo().create_logs(self.env.uid, self._name, self.ids, fnc.func_name,
                                        additional_log_values={'log_type': 'fast', 'message': message})
        res = fnc(self, *args, **kw)
        if do_audit:
            logger.info('\n'.join(filter(None, (log_prefix, message))))
        return res

    # propagate specific openerp attributes from method(fnc) to wrapper
    for attr in WRAPPED_ATTRS:
        if hasattr(fnc, attr):
            setattr(wrapper, attr, getattr(fnc, attr))
    wrapper._api = audit
    wrapper._orig = fnc

    return wrapper
