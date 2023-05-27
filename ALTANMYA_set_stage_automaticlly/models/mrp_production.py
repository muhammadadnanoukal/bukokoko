from odoo import api, fields, models


class Production(models.Model):
    _inherit = 'mrp.production'

    # def unlink(self):
    #     if self.opportunity_id:
    #         self.opportunity_id.set_stage()
    #     res = super().unlink()
    #     return res
    #
    @api.model_create_multi
    def create(self, vals_list):
        res = super(Production, self).create(vals_list)
        for production in res:
            sale_orders = production.procurement_group_id.mrp_production_ids.move_dest_ids.group_id.sale_id
            for order in sale_orders:
                if order.opportunity_id:
                    order.opportunity_id.set_stage('manufacturing', production.state)
        return res

    def write(self, vals):
        if vals.get('state', False):
            for production in self:
                sale_orders = production.procurement_group_id.mrp_production_ids.move_dest_ids.group_id.sale_id
                #sale_orders = self.env['sale.order'].search([('id', 'in', sale_order_ids)])
                for order in sale_orders:
                    if order.opportunity_id:
                        order.opportunity_id.set_stage('manufacturing', vals.get('state', False))
        return super().write(vals)

    def _action_cancel(self):
        res =super(Production, self)._action_cancel()
        if res:
            for production in self:
                sale_orders = production.procurement_group_id.mrp_production_ids.move_dest_ids.group_id.sale_id
                for order in sale_orders:
                    if order.opportunity_id:
                        order.opportunity_id.set_stage('manufacturing', production.state)
        return res

