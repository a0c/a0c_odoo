# -*- coding: utf-8 -*-
# © 2018 Anton Chepurov <anton.chepurov@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': "Audit Log Decorator",
    'version': "8.0.0.0.1",
    'author': 'Anton Chepurov <anton.chepurov@gmail.com>',
    'license': "AGPL-3",
    'category': "Tools",
    'summary': 'Decorate any method with @audit to auditlog it',
    'depends': [
        'auditlog',
    ],
    'data': [
        'views/auditlog_view.xml',
    ],
    'application': True,
    'installable': True,
}
