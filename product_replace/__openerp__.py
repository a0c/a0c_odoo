# -*- coding: utf-8 -*-
# © 2018 Anton Chepurov <anton.chepurov@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'Product Replace',
    'version': '8.0.0.0.1',
    'author': 'Anton Chepurov <anton.chepurov@gmail.com>',
    'license': "AGPL-3",
    'category': 'Tools',
    'summary': 'Replace a product with another one in various objects',
    'depends': [
        'product',
        'procurement',
        'many2many_ordered',
        'auditlog_decorator',
        'orm_enhanced',
    ],
    'data': [
        'security/product_replace_security.xml',
        'views/product_replace.xml',
        'views/product_replace_view.xml',
        'views/ir_model_fields.xml',
        'views/product.xml',
    ],
}
