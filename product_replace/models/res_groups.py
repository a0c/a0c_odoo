from openerp import api, models, SUPERUSER_ID
from openerp.exceptions import ValidationError


class res_groups(models.Model):
    _inherit = 'res.groups'

    def filter_admin_group(self):
        return self.filtered(lambda x: x == self.env.ref('product_replace.group_admin', raise_if_not_found=False))

    @api.constrains('users')
    def validate_admin_group(self):
        admin_group = self.filter_admin_group()
        if admin_group and admin_group.users.ids != [SUPERUSER_ID]:
            raise ValidationError('"%s" is a technical group that must only contain a single user - Administrator' % admin_group.name)

    @api.multi
    def unlink(self):
        admin_group = self.filter_admin_group()
        if admin_group:
            raise ValidationError('"%s" is a technical group not allowed to be deleted' % admin_group.name)
