from odoo import fields, models, _

class ProductTemplate(models.Model):
    _inherit = "product.template"

    estimated_installation_date_tmpl = fields.Float(string='Estimated Installation Days', store=True, )
    pricing_type_square_tmpl = fields.Boolean('Square Meter', default=True, )
    pricing_type_component_tmpl = fields.Boolean('Component', default=False, )


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _set_price_from_bom(self, boms_to_recompute=False):
        try:
            super(ProductProduct, self)._set_price_from_bom(boms_to_recompute)
        except:
            self.ensure_one()
            bom = self.env['mrp.bom']._bom_find(self)[self]
            if bom:
                self.standard_price = self._compute_bom_price(bom, boms_to_recompute=boms_to_recompute)
            else:
                bom = self.env['mrp.bom'].search([('byproduct_ids.product_id', '=', self.id)], order='sequence, product_id, id')
                if bom:
                    bom = bom[0]
                    price = self._compute_bom_price(bom, boms_to_recompute=boms_to_recompute, byproduct_bom=True)
                    if price:
                        self.standard_price = price