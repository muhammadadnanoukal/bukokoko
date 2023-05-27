from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError


class CrmLead(models.Model):
    """ Manufacturing Orders """
    _inherit = 'crm.lead'
    stage_id = fields.Many2one(
        'crm.stage', string='Stage', index=True, tracking=True,
        compute='_compute_stage_id', readonly=True, store=True,
        copy=False, group_expand='_read_group_stage_ids', ondelete='restrict',
        domain="['|', ('team_id', '=', False), ('team_id', '=', team_id)]")
    quotation_ids = fields.One2many('sale.order', 'opportunity_id', string='Opportunity')
    quotation_count = fields.Integer(compute='_compute_quotation_count')
    check_status = fields.Selection([('compatible', 'Compatible'), ('not_compatible', 'Not Compatible')],
                                    string='Stage Status', default='compatible', readonly=True)

    @api.onchange('quotation_ids')
    def _compute_quotation_count(self):
        first_stage = self.env['crm.stage'].search(['|', ('name', '=', 'New'), ('state', '=', '')])

        for rec in self:
            rec.quotation_count = len(self.quotation_ids)
            if rec.quotation_count == 0:
                if first_stage:
                    rec.check_status = 'compatible'
                    rec.stage_id = first_stage.id

    def set_stage(self, condition=None, status=None):
        print("set opportunity (%s%s) to stage with cond (%s,%s)"%(self,self.stage_id.name,condition,status))
        stage = self.env['crm.stage'].find_stage(condition, status)
        if stage and stage.sequence > self.stage_id.sequence:
            self.write({'stage_id': stage.id})
            print("the lead is pushed to upper stage %s"%stage.name)
            return True
        else:
            if not stage:
                print("There is no compatible stage with this condition (%s,%s) ." % (condition, status))
            if stage.sequence <= self.stage_id.sequence:
                print("the intended stage %s has lower sequence of current stage %s" %(stage.name , self.stage_id.name))
            # check is current stage is still compatible
            if not self.check_compatibility(self.stage_id):
                print("the current stage is no more compatible")
                # find compatible stage
                # for all stages that less than current stage
                stages = self.env['crm.stage'].search([('sequence','<',self.stage_id.sequence)], order='sequence desc')
                for stage in stages:
                    if self.check_compatibility(stage):
                        self.write({'stage_id': stage.id})
                        print("lead set to less stage %s"%stage.name)
                        return True
                print("there is no compatible stage for this lead")
                return False
            print("the current stage %s is compatible for this lead"%self.stage_id.name)
            return True

    def check_compatibility(self, stage):

        if stage.state == 'sales_status':
            order = self.env['sale.order'].search([('state', '=', stage.sales_status_selection), ('opportunity_id', '=', self.id)])
            return order
        if stage.state == 'manufacturing':
            orders = self.env['sale.order'].search([('state', 'in', ['sale','done']), ('opportunity_id', '=', self.id)])
            for order in orders:
                production_ids = self.env['mrp.production'].search([('state','=',stage.manufacturing_selection),
                                                                    ('id', 'in', order.mrp_production_ids.ids)])
                if production_ids:
                    return production_ids
            return False

        if stage.state == 'operation_type_sales':
            orders = self.order_ids.filtered_domain(self._get_lead_sale_order_domain())
            for order in orders:
                if order.picking_ids.filtered_domain([('picking_type_id','=',stage.operation_type_sales.id),
                                                                    ('state','=','done')]):
                    return True
            return False

        if stage.state == 'operation_type_manufacturing':
            orders = self.order_ids.filtered_domain(self._get_lead_sale_order_domain())
            for order in orders:
                for production_order in order.mrp_production_ids:
                    if production_order.picking_ids.filtered_domain([('picking_type_id', '=', stage.operation_type_manufacturing.id),
                                                          ('state', '=', 'done')]):
                        return True
            return False
        if not stage.state:
            return True
        return False

