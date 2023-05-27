from odoo import api, fields, models, _
from odoo.osv import expression


class CrmLead(models.Model):
    _inherit = "crm.lead"

    test = fields.Char(string='Test')
    contract_count = fields.Integer(compute='_compute_appointment_count')
    contract_ids = fields.One2many('contract', 'lead', string="contract")

    def action_open_contracts(self):
        """ Return the list of purchase orders the approval request created or
               affected in quantity. """
        action = {
            'name': 'Contracts',
            'view_type': 'tree',
            'view_mode': 'list,form',
            'res_model': 'contract',
            'type': 'ir.actions.act_window',
            'context': {
                'default_lead': self.id,
            },
            'domain': [('id', "in", self.contract_ids.ids)]
        }
        return action

    def _compute_appointment_count(self):
        for rec in self:
            # contract_count = self.env['contract'].search_count([])
            # rec.contract_count = contract_count
            rec.contract_count = len(self.contract_ids)

    @api.model
    def create(self, vals):
        res = super(CrmLead, self).create(vals)

        self.env['contract'].create({
            'name': 'Contract 1',
            'lead': res.id,
        })
        return res

    def action_view_sale_quotation(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("sale.action_quotations_with_onboarding")
        action['context'] = self._prepare_opportunity_quotation_context()
        action['context']['search_default_g_contract'] = 1
        action['domain'] = expression.AND(
            [[('opportunity_id', '=', self.id)], [('state', 'in', ('draft', 'sent', 'cancel', 'tentative approval', 'final approval', 'sale'))]])
        # quotations = self.order_ids.filtered_domain(self._get_lead_quotation_domain())
        # if len(quotations) == 1:
        #     action['views'] = [(self.env.ref('sale.view_order_form').id, 'form')]
        #     action['res_id'] = quotations.id
        return action

    @api.depends('order_ids.state', 'order_ids.currency_id', 'order_ids.amount_untaxed', 'order_ids.date_order',
                 'order_ids.company_id')
    def _compute_sale_data(self):
        for lead in self:
            company_currency = lead.company_currency or self.env.company.currency_id
            sale_orders = lead.order_ids.filtered_domain(self._get_lead_sale_order_domain())
            lead.sale_amount_total = sum(
                order.currency_id._convert(
                    order.amount_untaxed, company_currency, order.company_id, order.date_order or fields.Date.today()
                )
                for order in sale_orders
            )
            lead.quotation_count = len(lead.order_ids)
            lead.sale_order_count = len(sale_orders)
