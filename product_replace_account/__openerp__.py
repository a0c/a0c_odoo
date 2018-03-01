# -*- coding: utf-8 -*-
# © 2018 Anton Chepurov <anton.chepurov@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'Product Replace in Account',
    'version': '8.0.0.0.1',
    'author': 'Anton Chepurov <anton.chepurov@gmail.com>',
    'license': "AGPL-3",
    'category': 'Tools',
    'summary': 'Replace a product with another one in various account objects',
    'description': """
Product Replace in Account
==========================
""",
    'depends': [
        'product_replace',
        'account',
    ],
    'data': [
        'views/account.xml',
        'views/product_replace_account.xml',
        'views/product_replace_view.xml',
    ],
    'auto_install': True,
}
