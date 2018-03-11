from openerp.exceptions import Warning
from openerp.models import api, BaseModel
from openerp.tools.safe_eval import safe_eval as eval


def _with_xml_id_prefix(self, act_xml_id):
    raise Warning("Short act_xml_id like '%s' can only be used in _read_act_window() and action() once you implement "
                  "_with_xml_id_prefix(self, act_xml_id) on BaseModel to return a default system-wide prefix for XML_ID-s" % act_xml_id)

BaseModel._with_xml_id_prefix = _with_xml_id_prefix


def xml_id_rec(self, xml_id):
    if '.' not in xml_id:
        xml_id = self._with_xml_id_prefix(xml_id)
    return self.env.ref(xml_id)


def _resolve_action(self, act_xml_id):
    if isinstance(act_xml_id, basestring):
        act = xml_id_rec(self, act_xml_id)
    elif isinstance(act_xml_id, (int, long)):
        act = self.env['ir.actions.act_window'].browse(act_xml_id)
    else:
        act = self.env['ir.actions.act_window'].search([('res_model', '=', self._name)], order='id', limit=1)
    if not act:
        return {
            'name': self._description,
            'view_type': 'form',
            'view_mode': 'tree,form',
            'view_id': [False],
            'views': [(False, 'tree'), (False, 'form')],
            'res_model': self._name,
            'type': 'ir.actions.act_window',
            'context': self.env.user.context_get(),
            'target': 'current',
            'domain': [],
        }
    return act.read(['name', 'view_mode', 'view_id', 'view_type', 'views', 'res_model', 'type', 'target', 'domain', 'context'])[0]

BaseModel._resolve_action = _resolve_action


def eval_if_str(line, context_globals):
    return eval(line.strip(), context_globals) if isinstance(line, basestring) else line

def _read_act_window(self, act_xml_id, context_globals=None, act_update=None, ctx_update=None, res_id=False, form_view_id=False):
    act = self._resolve_action(act_xml_id)
    act['context'] = eval_if_str(act['context'], context_globals)
    if act.get('domain'):
        act['domain'] = eval_if_str(act['domain'], context_globals)
    if ctx_update is not None:
        act['context'].update(ctx_update)
    if act_update is not None:
        act.update(act_update)
    if res_id:
        act['res_id'] = res_id
    if form_view_id:
        act['views'] = [(form_view_id, 'form')]
    return act

BaseModel._read_act_window = _read_act_window


@api.multi
def action(self, action_xmlid, ctx_upd=False):
    if not self and not self._context.get('allow_empty', False):
        return True
    ctx = dict(self.env.user.context_get(), uid=self._uid, active_ids=self.ids, active_model=self._name)
    if self.ids:
        ctx['active_id'] = self.ids[0]
    if ctx_upd:
        ctx.update(ctx_upd)
    return self._read_act_window(action_xmlid, context_globals=dict(ctx), ctx_update=ctx)

BaseModel.action = action


@api.multi
def action_view(self, form_xmlid, action_xmlid=None, ctx_upd=False):
    # to allow calls from other models (e.g. self.picking_id.action_view())
    # need a clean ctx => use action() instead of _read_act_window()
    res = self.action(action_xmlid, ctx_upd)
    if len(self.ids) == 1 and form_xmlid:
        res['res_id'] = self.id
        res['views'] = [(xml_id_rec(self, form_xmlid).id, 'form')]
    else:
        res['domain'] = "[('id','in',%s)]" % (str(self.ids),)
    return res

BaseModel.action_view = action_view


@api.multi
def action_view_tree(self, action_xmlid=None, ctx_upd=False):
    return self.action_view(None, action_xmlid=action_xmlid, ctx_upd=ctx_upd)

BaseModel.action_view_tree = action_view_tree
