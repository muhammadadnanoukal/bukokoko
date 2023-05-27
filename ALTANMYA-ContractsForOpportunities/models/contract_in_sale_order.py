# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ContractSaleOrder(models.Model):
    _inherit = "sale.order"

    opportunity_contract_ids = fields.One2many('contract', 'related_sale_order_id', compute='_opportunity_contract_ids')

    @api.depends('opportunity_id')
    def _opportunity_contract_ids(self):
        for rec in self:
            if rec.opportunity_id.id:
                if len(rec.opportunity_id.contract_ids) != 0:
                    for c in rec.opportunity_id.contract_ids:
                        rec.opportunity_contract_ids = [(4, c.id)]
                        if not rec.opportunity_id.id:
                            print('3')

                        else:
                            if not rec.contract:
                                rec.contract = rec.opportunity_id.contract_ids[0].id
                else:
                    rec.opportunity_contract_ids = [(5, 0, 0)]
                    rec.contract = False

            else:
                rec.opportunity_contract_ids = [(5, 0, 0)]
                rec.contract = False

    contract = fields.Many2one('contract', string="Contract", domain="[('id', 'in', opportunity_contract_ids)]")

    state = fields.Selection([
        ('draft', "Quotation"),
        ('sent', "Quotation Sent"),
        ('tentative approval', 'Tentative Approval'),
        ('final approval', 'Final Approval'),
        ('sale', "Sales Order"),
        ('done', "Locked"),
        ('cancel', "Cancelled"),
    ], string="Status",
        readonly=True, copy=False, index=True,
        tracking=3, default='draft')

    # @api.depends('contract')
    # def get_selection_states(self):
    #     print(self.opportunity_id)
    #     print(self.id)
    #     if not self.opportunity_id:
    #         print('1')
    #         selection = [
    #             ('draft', "Quotation"),
    #             ('sent', "Quotation Sent"),
    #             ('sale', "Sales Order"),
    #             ('done', "Locked"),
    #             ('cancel', "Cancelled"),
    #         ]
    #     else:
    #         print('2')
    #         selection = [
    #             ('draft', "Quotation"),
    #             ('sent', "Quotation Sent"),
    #             ('tentative approval', 'Tentative Approval'),
    #             ('final approval', 'Final Approval'),
    #             ('sale', "Sales Order"),
    #             ('done', "Locked"),
    #             ('cancel', "Cancelled"),
    #         ]
    #     return selection

    def action_tentative_confirm(self):
        payments_leads_contracts_ids = self.env['account.payment'].search([('contract.id', '=', self.contract.id)])
        print(payments_leads_contracts_ids)
        tot = 0
        for record in payments_leads_contracts_ids:
            test = record.filtered(lambda attach: attach.state == 'posted')
            tot += test.amount
        twenty_percent_of_quotation = (self.amount_total * 20) / 100
        if tot >= twenty_percent_of_quotation:
            sale_orders = self.env['sale.order'].search([('opportunity_id', '=', self.opportunity_id.id)])
            contract_id = self.contract.id
            sale_orders = sale_orders.filtered(lambda l: l.contract.id == contract_id)
            for id1 in sale_orders.ids:
                if id1 != self.id:
                    self.env['sale.order'].browse(id1).state = 'cancel'
            for rec in self:
                rec.state = 'tentative approval'

        else:
            raise UserError(
                _("You cannot approve this quotation because the total payments does not achieve 20 percent of the value of quotation"))

    def action_final_confirm(self):
        payments_leads_contracts_ids = self.env['account.payment'].search([('contract.id', '=', self.contract.id)])
        tot = 0
        for record in payments_leads_contracts_ids:
            test = record.filtered(lambda attach: attach.state == 'posted')
            tot += test.amount
        twenty_percent_of_quotation = (self.amount_total * 50) / 100
        if tot >= twenty_percent_of_quotation:
            for rec in self:
                rec.state = 'final approval'
        else:
            raise UserError(
                _("You cannot approve this quotation because the total payments does not achieve 50 percent of the value of quotation"))
