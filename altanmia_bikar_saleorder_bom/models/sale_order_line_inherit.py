import logging
from odoo import api, fields, models, _
from collections import defaultdict

from odoo.osv.expression import AND

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = "sale.order"
    estimated_installation_date_total = fields.Float(string="Estimated Installation Days", store=True, tracking=4,
                                                     readonly=True, compute='_compute_installation_amounts')


    def update_prices_from_bom(self):
        self.ensure_one()
        lines_to_update = []
        for line in self.order_line:
            lines_to_update.append((1, line.id, {'price_unit': line.bom_id.total_amount}))
        self.update({'order_line': lines_to_update})
        # self.show_update_price_unit = False
        self.message_post(body=_("Product prices have been recomputed according to each bom selected"))

    @api.depends('order_line.total_installation_date')
    def _compute_installation_amounts(self):
        for order in self:
            order_lines = order.order_line.filtered(lambda x: not x.display_type)
            order.estimated_installation_date_total = sum(order_lines.mapped('total_installation_date'))

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    bom_id = fields.Many2one(
        'mrp.bom', 'Component', readonly=False,
        domain="""[
        '&',
            '|',
                ('company_id', '=', False),
                ('company_id', '=', company_id),
            '&',
               ('product_tmpl_id','=',product_template_id),
        ('worked', '=', True)]""",
        check_company=True, compute='_compute_bom_id', store=True, precompute=True,
        help="Bill of Materials allow you to define the list of required components to make a finished product.")

    qty_to_deliver = fields.Float(compute='_compute_qty_to_deliver', digits='Product Unit of Measure')
    display_qty_widget = fields.Boolean(compute='_compute_qty_to_deliver')
    total_installation_date = fields.Float('Total Installation Date',
                                             store=True, compute='_compute_estimated_installation_date_total')

    pricelist_id = fields.Many2one('product.pricelist', 'Pricelist', related="order_id.pricelist_id", store=True,
                                   readonly=False)
    price_unit = fields.Float('Unit Price', required=True, related="bom_id.total_amount", store=True)
    testing_price = fields.Float("customize price", related="bom_id.total_amount")

    @api.depends('product_id')
    def _compute_bom_id(self):
        for sol in self:
            if not sol.product_id and not sol.bom_id:
                sol.bom_id = False
                continue
            boms_by_product = self.env['mrp.bom'].with_context(active_test=True, just_worked=True)._bom_find(sol.product_id,
                                                                                           company_id=sol.company_id.id,
                                                                                           bom_type='normal')
            if not sol.bom_id or sol.bom_id.product_tmpl_id != sol.product_template_id or (
                    sol.bom_id.product_id and sol.bom_id.product_id != sol.product_id):
                bom = boms_by_product[sol.product_id]
                sol.bom_id = bom.id or False

    @api.onchange('price_unit')
    def _onchange_total_amount(self):
        for line in self:
            if line.bom_id:
                line.price_unit = line.bom_id.total_amount

    @api.onchange('product_uom_qty', 'bom_id')
    def _compute_estimated_installation_date_total(self):
        for rec in self:
            rec.total_installation_date = rec.bom_id.total_installation_date
            rec.total_installation_date = rec.total_installation_date * rec.product_uom_qty

    @api.onchange('product_template_id', 'bom_id')
    def onchange_product_template_id(self):
        for line in self:
            return {'domain': {'bom_id': ['|', ('product_tmpl_id', '=', line.product_template_id.id), (
                'byproduct_ids.product_id.product_tmpl_id', '=', line.product_template_id.id)]}}

    @api.onchange('bom_id')
    def _onchange_bom_id(self):
        for record in self:
            if record.bom_id and record.bom_id.product_id:
                record.product_id = record.bom_id.product_id

    @api.depends('product_uom_qty', 'qty_delivered', 'product_id', 'state')
    def _compute_qty_to_deliver(self):
        """The inventory widget should now be visible in more cases if the product is consumable."""
        for line in self:
            line.qty_to_deliver = line.product_uom_qty - line.qty_delivered
            if line.state in ('draft', 'sent',
                              'sale') and line.product_type == 'product' and line.product_uom and line.qty_to_deliver > 0:
                if line.state == 'sale' and not line.move_ids:
                    line.display_qty_widget = False
                else:
                    line.display_qty_widget = True
            else:
                line.display_qty_widget = False
        for line in self:
            if line.bom_id:
                # Hide the widget for kits since forecast doesn't support them.
                boms = self.env['mrp.bom']
                if line.state == 'sale':
                    boms = line.move_ids.mapped('bom_line_id.bom_id')
                elif line.state in ['draft', 'sent'] and line.product_id:
                    bom_id = [line.bom_id.id] if line.bom_id else False
                    boms = \
                        boms._bom_find(line.product_id, company_id=line.company_id.id,
                                       bom_type=['phantom'])[
                            line.product_id]
                relevant_bom = boms.filtered(
                    lambda b: (b.type == 'phantom') and
                              (b.product_id == line.product_id or
                               (
                                       b.product_tmpl_id == line.product_id.product_tmpl_id and not b.product_id)))
                if relevant_bom:
                    line.display_qty_widget = False
                    continue
                if line.state == 'draft' and line.product_type == 'consu':
                    components = line.product_id.get_components()
                    if components and components != [line.product_id.id]:
                        line.display_qty_widget = True
            else:
                boms = self.env['mrp.bom']
                if line.state == 'sale':
                    boms = line.move_ids.mapped('bom_line_id.bom_id')
                elif line.state in ['draft', 'sent'] and line.product_id:
                    boms = \
                        boms._bom_find(line.product_id, company_id=line.company_id.id,
                                       bom_type=['phantom'])[
                            line.product_id]
                relevant_bom = boms.filtered(lambda b: (b.type == 'phantom') and
                                                       (b.product_id == line.product_id or
                                                        (
                                                                b.product_tmpl_id == line.product_id.product_tmpl_id and not b.product_id)))
                if relevant_bom:
                    line.display_qty_widget = False
                    continue
                if line.state == 'draft' and line.product_type == 'consu':
                    components = line.product_id.get_components()
                    if components and components != [line.product_id.id]:
                        line.display_qty_widget = True