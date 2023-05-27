from odoo import api, fields, models, _, Command


class CrmStage(models.Model):
    _inherit = 'crm.stage'

    new_stage = fields.Boolean(string='New Stage')
    state = fields.Selection([
        ('sales_status', 'Sales Status'),
        ('manufacturing', 'Manufacturing'),
        ('operation_type_sales', 'Operation Type-Sales'),
        ('operation_type_manufacturing', 'Operation Type-Manufacturing'),

    ])
    sales_status_selection = fields.Selection([
        ('draft', "Quotation"),
        ('sent', "Quotation Sent"),
        ('tentative approval', 'Tentative/Final Approval'),
        ('sale', "Sales Order"),
        ('done', "Locked"),
        ('cancel', "Cancelled"),
    ])
    manufacturing_selection = fields.Selection([
        ('draft', 'Draft'),
        ('approve', 'Approved'),
        ('confirmed', 'Confirmed'),
        ('progress', 'In Progress'),
        ('to_close', 'To Close'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')])

    operation_type_sales = fields.Many2one('stock.picking.type', string="Operation Type-Sales")
    operation_type_manufacturing = fields.Many2one('stock.picking.type', string="Operation Type-Manufacturing")

    def find_stage(self, condition, status):
        if not (condition and status):
            return self.search([('state', '=', False)],limit=1, order='sequence asc')

        if type(condition) == str:
            if condition == 'sales_status':
                return self.search([('state', '=', condition), ('sales_status_selection','=',status)],limit=1)
            if condition == 'manufacturing':
                return self.search([('state', '=', condition), ('manufacturing_selection','=',status)],limit=1)

        if type(status) == int or isinstance(status, type(self.env['stock.picking.type'])):
            pick_id = status if type(status) == int else status.id
            if condition == 'operation_type_sales':
                return self.search([('state', '=', condition), ('operation_type_sales','=',pick_id)],limit=1)
            if condition == 'operation_type_manufacturing':
                return self.search([('state', '=', condition), ('operation_type_manufacturing','=',pick_id)],limit=1)

        return False