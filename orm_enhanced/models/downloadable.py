from openerp import api, fields, models


class downloadable(models.AbstractModel):
    _name = 'downloadable'

    file_data = fields.Binary('File')
    file_name = fields.Char('File Name')

    @api.model
    def download(self, file_name, file_data):
        return self.create({'file_name': file_name, 'file_data': file_data}).action_download()

    @api.multi
    def action_download(self, field='file_data', filename_field='file_name'):
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/binary/saveas?model=%s&id=%s&field=%s&filename_field=%s' %
                   (self._name, self.id, field, filename_field),
            'target': 'self',
        }
