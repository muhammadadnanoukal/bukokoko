# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'ALTANMYA-ApproveButtonForManufacture',
    'version': '1.2',
    'summary': 'Hospital Management Software',
    'sequence': -100,
    'description': """ALTANMYA-Bikar""",
    'category': 'productivity',
    'depends': ['crm', 'sale_management', 'mrp'],
    'data': [
        # 'security/ir.model.access.csv',
        # 'data/data.xml',
        # 'views/contract_smart_button.xml',
        # 'views/payments_smart_button.xml',
        # 'views/contract_views.xml',
        # 'views/contract_in_sale_order_views.xml',
        'views/mrp_production_inherit_views.xml',
        # 'wizard/create_appointment_view.xml',
        # 'reports/report.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
