from odoo import api, fields, models


class PaymentAccountFields(models.Model):
    _inherit = "account.payment"

    opportunity_contract_ids = fields.One2many('contract', 'related_sale_order_id', compute='_opportunity_contract_ids')
    opportunity_id = fields.Many2one('crm.lead', string='Opportunity', readonly=True, default=lambda self: self.id)

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
                                # rec.opportunity_id = rec.opportunity_id.contract_ids[0].id
                                print(rec.contract)
                else:
                    rec.opportunity_contract_ids = [[(5, 0, 0)]]
                    rec.contract = False

            else:
                rec.opportunity_contract_ids = [[(5, 0, 0)]]
                rec.contract = False

    contract = fields.Many2one('contract', string="Contract", domain="[('id', 'in', opportunity_contract_ids)]", )
    # contract = fields.Many2one('contract', string="Contract")
