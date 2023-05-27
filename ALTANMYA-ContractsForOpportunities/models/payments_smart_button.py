from odoo import api, fields, models, _


class PaymentAccountButton(models.Model):
    _inherit = "crm.lead"

    payment_count = fields.Integer(compute='_compute_payments_count')
    payment_ids = fields.One2many('account.payment', 'opportunity_id', string='Opportunity')

    def action_open_payments(self):
        action = {
            'name': 'Payments',
            'view_type': 'tree',
            'view_mode': 'list,form',
            'res_model': 'account.payment',
            'type': 'ir.actions.act_window',
            'context': {
                'default_opportunity_id': self.id,
                'default_partner_id': self.partner_id.id,
            },
            'domain': [('id', "in", self.payment_ids.ids)]
        }
        return action

    def _compute_payments_count(self):
        for rec in self:
            rec.payment_count = len(self.payment_ids)
