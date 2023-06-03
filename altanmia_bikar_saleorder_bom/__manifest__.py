# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Bikar Sale Order BOM',
    'version' : '0.0.0',
    'summary': 'Get user ability to control product BOM upon creating sale order ',
    'sequence': -40,
    'description':'',
    'category': 'Sales/Sales',
    'website': 'https://www.odoo.com/app/invoicing',
    'images' : [],
    'depends' : ['mrp', 'sale', 'stock', 'sale_mrp'],
    'data': [
        'views/sale_order_view.xml',
        'views/mrp_bom_views.xml',
        'views/product_views.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': True,
    'assets': {},
    'license': 'LGPL-3',
}
