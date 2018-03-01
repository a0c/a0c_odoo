import logging

from openerp import fields, models
from openerp.api import WRAPPED_ATTRS
from openerp.exceptions import Warning

logger = logging.getLogger('[AUDIT]')


class AuditlogLog(models.Model):
    _inherit = 'auditlog.log'
    _order = "create_date desc, id desc"

    message = fields.Html(readonly=1)
    first_line = fields.Char(compute='_first_line')

    def _first_line(self):
        for x in self:
            x.first_line = x.message and un_html(x.message.split('<br>', 1)[0])


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
        rule_obj = get_rule_obj(self)
        do_audit = self and not self._context.get('no_audit')
        if do_audit:
            if 'audit_msgs' not in self._context:
                self = self.with_context(audit_msgs=[])
            if self._name not in rule_obj.pool._auditlog_model_cache:
                rule_obj.pool._auditlog_model_cache[self._name] = self.env['ir.model'].search([('model', '=', self._name)], limit=1).id
            # generate log message and create logs before calling fnc, cos it can delete self records
            log_prefix, message = get_audit_message(self, *args, **kw)
            logs = rule_obj.sudo().create_logs(self.env.uid, self._name, self.ids, fnc.func_name,
                                               additional_log_values={'log_type': 'fast', 'message': html_newlines(message)})
        res = fnc(self, *args, **kw)
        if do_audit:
            audit_msgs = '\n'.join(self._context['audit_msgs'])
            if audit_msgs:
                message = '%s\n\n%s' % (message, audit_msgs)
                logs.write({'message': html_newlines(message)})
            logger.info('\n'.join(filter(None, (log_prefix, un_html(message)))))
        return res

    def get_rule_obj(self):
        try:
            return self.env['auditlog.rule']
        except:
            raise Warning('@audit decorator only supports API 8 and must be the last decorator on the method')

    # propagate specific openerp attributes from method(fnc) to wrapper
    for attr in WRAPPED_ATTRS:
        if hasattr(fnc, attr):
            setattr(wrapper, attr, getattr(fnc, attr))
    wrapper._api = audit
    wrapper._orig = fnc

    return wrapper


def html_newlines(msg):
    return msg.replace('\n', '<br>\n')


def un_html(msg):
    for x, r in ('<b>', ''), ('</b>', ''), ('&emsp;', '  '), ('<p>', ''), ('</p>', ''), ('&gt;', '>'), ('&lt;', '<'):
        msg = msg.replace(x, r)
    return msg
