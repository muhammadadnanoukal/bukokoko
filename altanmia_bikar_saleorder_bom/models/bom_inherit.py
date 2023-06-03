from odoo import api, fields, models, _
from odoo.osv.expression import AND


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    worked = fields.Boolean("Active Bom", default=True)

    pricelist_id = fields.Many2one(
        comodel_name='product.pricelist',
        string="Pricelist",
        store=True, readonly=False, check_company=True, # Unrequired company
        tracking=1,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")

    code = fields.Char('Reference')
    pricing_type_square = fields.Boolean('Square Meter', default=True, )
    pricing_type_component = fields.Boolean('Component', default=False, )
    total_installation_date = fields.Float('Total Installation Date', compute='_compute_installation_amount',
                                           store=True, tracking=True)
    total_amount = fields.Float('Total Amount', compute='_compute_amount', store=True, tracking=True)

    currency_id = fields.Many2one(
        related='pricelist_id.currency_id',
        depends=["pricelist_id"],
        store=True, precompute=True, ondelete="restrict")

    @api.depends('bom_line_ids.estimated_installation_date')
    def _compute_installation_amount(self):
        for rec in self:
            rec.total_installation_date = sum(rec.bom_line_ids.mapped('estimated_installation_date'))

    @api.onchange('product_tmpl_id')
    def onchange_product_tmpl_id(self):
        if self.product_tmpl_id:
            self.product_uom_id = self.product_tmpl_id.uom_id.id
            if self.product_id.product_tmpl_id != self.product_tmpl_id:
                self.product_id = False
            self.bom_line_ids.bom_product_template_attribute_value_ids = False
            self.operation_ids.bom_product_template_attribute_value_ids = False
            self.byproduct_ids.bom_product_template_attribute_value_ids = False

            domain = [('product_tmpl_id', '=', self.product_tmpl_id.id)]
            if self.id.origin:
                domain.append(('id', '!=', self.id.origin))
        if self._context.get('default_name', False):
            self.code = self._context['default_name']

    @api.depends('bom_line_ids.price_unit', 'bom_line_ids.product_qty', 'bom_line_ids.price_subtotal')
    def _compute_amount(self):
        for rec in self:
            rec.total_amount = sum(rec.bom_line_ids.mapped('price_subtotal'))

    @api.onchange('pricelist_id')
    def _onchange_pricelist_id(self):
        for line in self.bom_line_ids:
            if line.product_id:
                line._compute_pricelist_item_id()
                line._compute_price_unit()

    @api.model
    def _bom_find_domain(self, products, picking_type=None, company_id=False, bom_type=False):
        domain = super(MrpBom, self)._bom_find_domain(products, picking_type, company_id, bom_type)
        if self.env.context.get("just_worked", False):
            domain = AND([domain, [('worked', '=', True)]])
        return domain

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self.env['mrp.bom'].search([
                ('product_id','=',vals.get('product_id', False)),
                ('type','=',vals.get('type','normal')),
                ('worked', '=', True)]).write({'worked':False})

            vals['worked'] = True

            if self.env.context.get("new_product_variant", False):


                attr = self.env['product.attribute'].search([('name','=','BOM')], limit=1)
                if not attr:
                    attr = self.env['product.attribute'].create({'name': 'BOM'})

                variant_value = self.env['product.attribute.value'].create({
                    'name': vals['code'],
                    'attribute_id': attr.id,
                })
                attr_value_line = self.env['product.template.attribute.line'].search([('product_tmpl_id','=',vals['product_tmpl_id']), ('attribute_id','=',attr.id)])
                if not attr_value_line:
                    attr_value_line = self.env['product.template.attribute.line'].create({
                        'product_tmpl_id': vals['product_tmpl_id'],
                        'attribute_id': attr.id,
                        'value_ids': [(6, 0, [variant_value.id ])],
                    })
                else:
                    attr_value_line.write({
                        'value_ids': [(6, 0, [variant_value.id] + attr_value_line.value_ids.ids)],
                    })
                template = self.env['product.template'].browse(vals['product_tmpl_id'])
                value = self._get_product_template_attribute_value(variant_value, template)
                product = template._get_variant_for_combination(value)
                vals['product_id'] = product.id


        return super(MrpBom, self).create(vals_list)

    def _get_product_template_attribute_value(self, product_attribute_value, model):
        """
            Return the `product.template.attribute.value` matching
                `product_attribute_value` for self.

            :param: recordset of one product.attribute.value
            :return: recordset of one product.template.attribute.value if found
                else empty
        """

        return model.valid_product_template_attribute_line_ids.filtered(
            lambda l: l.attribute_id == product_attribute_value.attribute_id
        ).product_template_value_ids.filtered(
            lambda v: v.product_attribute_value_id == product_attribute_value
        )


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    last_price = fields.Float(string='Last Price')
    estimated_installation_date = fields.Float(string='Estimated Installation Days', readonly=True, store=True, )
    attachments_count = fields.Integer(string='Attachment Count', compute='_compute_attachments_count')
    price_unit = fields.Float(
        string="Unit Price",
        compute='_compute_price_unit',
        digits='Product Price',
        store=True, readonly=False, required=True, precompute=True)
    price_subtotal = fields.Float('Subtotal', compute='_compute_price_subtotal', default=0.0)
    check_field = fields.Boolean('Check', compute='get_user')

    currency_id = fields.Many2one(
        related='bom_id.currency_id',
        depends=['bom_id.currency_id'],
        store=True, precompute=True)

    pricelist_item_id = fields.Many2one(
        comodel_name='product.pricelist.item',
        compute='_compute_pricelist_item_id')

    @api.onchange('product_id', 'product_qty')
    def _compute_installation_date(self):
        res = self.product_id.product_tmpl_id.estimated_installation_date_tmpl * self.product_qty
        self.estimated_installation_date = res

    @api.depends('product_id', 'product_uom_id', 'product_qty')
    def _compute_pricelist_item_id(self):
        for line in self:
            if not line.product_id or not line.bom_id.pricelist_id:
                line.pricelist_item_id = False
            else:
                line.pricelist_item_id = line.bom_id.pricelist_id._get_product_rule(
                    line.product_id,
                    line.product_qty or 1.0,
                    uom=line.product_uom_id,
                    date=fields.Date.today(),
                )
        print("_compute_pricelist_item_id", line.pricelist_item_id)

    @api.depends('product_id', 'product_uom_id', 'product_qty')
    def _compute_price_unit(self):
        for line in self:
            if not line.product_id or not line.bom_id.pricelist_id:
                line.price_unit = 0.0
            else:
                price = line.with_company(line.company_id)._get_display_price()
                line.price_unit = line.product_id._get_tax_included_unit_price(
                    line.company_id,
                    line.bom_id.currency_id,
                    fields.Date.today(),
                    'sale',
                    product_price_unit=price,
                    product_currency=line.currency_id
                )
        print("_compute_price_unit", line.pricelist_item_id, line.product_id , line.bom_id.pricelist_id)

    def _get_display_price(self):
        self.ensure_one()

        pricelist_price = self._get_pricelist_price()

        if self.bom_id.pricelist_id.discount_policy == 'with_discount':
            return pricelist_price

        if not self.pricelist_item_id:
            # No pricelist rule found => no discount from pricelist
            return pricelist_price

        base_price = self._get_pricelist_price_before_discount()

        # negative discounts (= surcharge) are included in the display price
        return max(base_price, pricelist_price)

    def _get_pricelist_price(self):
        self.ensure_one()
        self.product_id.ensure_one()

        pricelist_rule = self.pricelist_item_id
        order_date = fields.Date.today()
        product = self.product_id
        qty = self.product_qty or 1.0
        uom = self.product_uom_id or self.product_id.uom_id

        price = pricelist_rule._compute_price(
            product, qty, uom, order_date, currency=self.currency_id)

        return price

    def _get_pricelist_price_before_discount(self):
        """Compute the price used as base for the pricelist price computation.

        :return: the product sales price in the order currency (without taxes)
        :rtype: float
        """
        self.ensure_one()
        self.product_id.ensure_one()

        pricelist_rule = self.pricelist_item_id
        order_date = fields.Date.today()
        product = self.product_id
        qty = self.product_qty or 1.0
        uom = self.product_uom_id

        if pricelist_rule:
            pricelist_item = pricelist_rule
            if pricelist_item.pricelist_id.discount_policy == 'without_discount':
                # Find the lowest pricelist rule whose pricelist is configured
                # to show the discount to the customer.
                while pricelist_item.base == 'pricelist' and pricelist_item.base_pricelist_id.discount_policy == 'without_discount':
                    rule_id = pricelist_item.base_pricelist_id._get_product_rule(
                        product, qty, uom=uom, date=order_date)
                    pricelist_item = self.env['product.pricelist.item'].browse(rule_id)

            pricelist_rule = pricelist_item

        price = pricelist_rule._compute_base_price(
            product,
            qty,
            uom,
            order_date,
            target_currency=self.currency_id,
        )

        return price

    @api.depends('price_unit', 'product_qty')
    def _compute_price_subtotal(self):
        for line in self:
            line.price_subtotal = line.price_unit * line.product_qty

    @api.depends('price_unit')
    def get_user(self):
        if not self.env.user.has_group('sales_team.group_sale_manager'):
            self.check_field = False
        else:
            self.check_field = True