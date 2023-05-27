# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'ALTANMYA-SetStageAutomaticlly',
    'version': '1.0',
    'summary': 'ALTANMYA-Bikar',
    'author': 'ALTANMYA - TECHNOLOGY SOLUTIONS',
    'company': 'ALTANMYA - TECHNOLOGY SOLUTIONS Part of ALTANMYA GROUP',
    'website': "http://tech.altanmya.net",
    'category': 'Manufacturing/Manufacturing',
    'depends': ['mrp', 'sale', 'stock', 'sale_mrp', 'crm'],
    'description': "Bikar MRP Extension",
    'data': [
        'views/crm_stage_selection.xml',
        'views/crm_lead_view.xml',
        'data/data.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3'
}
