# -*- coding: utf-8 -*-
# © 2018 Anton Chepurov <anton.chepurov@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'Product Replace in Stock',
    'version': '8.0.0.0.1',
    'author': 'Anton Chepurov <anton.chepurov@gmail.com>',
    'license': "AGPL-3",
    'category': 'Tools',
    'summary': 'Replace a product with another one in various stock objects',
    'description': """
Product Replace in Stock
========================
""",
    'depends': [
        'product_replace',
        'stock',
    ],
    'data': [
        'views/product_replace_stock.xml',
        'views/product_replace_view.xml',
        'views/stock.xml',
    ],
    'auto_install': True,
}
