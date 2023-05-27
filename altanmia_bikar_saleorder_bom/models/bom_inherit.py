from odoo import api, fields, models, _
from odoo.osv.expression import AND


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    worked = fields.Boolean("Active Bom", default=True)
    pricelist_id = fields.Many2one('product.pricelist', 'Pricelist', readonly=False)
    code = fields.Char('Reference')
    pricing_type_square = fields.Boolean('Square Meter', default=True, )
    pricing_type_component = fields.Boolean('Component', default=False, )
    total_installation_date = fields.Float('Total Installation Date', compute='_compute_installation_amount',
                                           store=True, tracking=True)
    total_amount = fields.Float('Total Amount', compute='_compute_amount', store=True, tracking=True)

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
                line.price_unit = line.compute_price_unit()

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
    price_unit = fields.Float('Unit Price', required=True, default=0.0)
    price_subtotal = fields.Float('Subtotal', compute='_compute_price_subtotal', default=0.0)
    check_field = fields.Boolean('Check', compute='get_user')

    @api.onchange('product_id', 'product_qty')
    def _compute_installation_date(self):
        res = self.product_id.product_tmpl_id.estimated_installation_date_tmpl * self.product_qty
        self.estimated_installation_date = res

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            # Compute Last Price
            self._cr.execute(
                'SELECT price FROM product_supplierinfo WHERE product_tmpl_id = {} ORDER BY id DESC LIMIT 1'.format(
                    self.product_id.product_tmpl_id.id)
            )
            _res = self._cr.dictfetchall()
            if _res is not None and len(_res) != 0:
                self.last_price = _res[0].get('price')
            else:
                self.last_price = 0
            # Compute Price Unit
            self.price_unit = self.compute_price_unit()

    def compute_price_unit(self):
        price_unit = 0.0
        from_pricelist = self.env['product.pricelist.item'].search(
            [('product_tmpl_id', '=', self.product_id.product_tmpl_id.id),
             ('pricelist_id', '=', self.bom_id.pricelist_id.id)], limit=1)
        if not from_pricelist:
            from_template = self.env['product.template'].search([('id', '=', self.product_id.product_tmpl_id.id)],
                                                                limit=1)
            if from_template:
                price_unit = from_template.list_price
        else:
            price_unit = from_pricelist.fixed_price

        return price_unit

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