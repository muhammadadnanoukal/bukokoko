# -*- coding: utf-8 -*-
from odoo import api, fields, models


class Contract(models.Model):
    _name = "contract"
    _inherit = "mail.thread"

    related_sale_order_id = fields.Many2one('sale.order')
    name = fields.Char(required=True)
    lead = fields.Many2one('crm.lead', string="Lead/Opportunity", readonly=True, default=lambda self: self.id)


