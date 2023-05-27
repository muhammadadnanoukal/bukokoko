# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
import logging

from odoo import SUPERUSER_ID, models, registry
from odoo.addons.stock.models.stock_rule import ProcurementException
from odoo.tools import float_compare, frozendict, split_every

from psycopg2 import OperationalError
_logger = logging.getLogger(__name__)


# class StockWarehouseOrderpoint(models.Model):
#     """ Defines Minimum stock rules. """
#     _inherit = "stock.warehouse.orderpoint"
#
#     def _prepare_procurement_values(self, date=False, group=False, stock_move=False):
#         res = super(StockWarehouseOrderpoint, self)._prepare_procurement_values(date,group)
#         res['move_dest_ids'] = stock_move
#         return res
#
#     def _procure_orderpoint_confirm(self, use_new_cursor=False, company_id=None, raise_user_error=True, stock_move=False):
#         """ Create procurements based on orderpoints.
#         :param bool use_new_cursor: if set, use a dedicated cursor and auto-commit after processing
#             1000 orderpoints.
#             This is appropriate for batch jobs only.
#         """
#         self = self.with_company(company_id)
#
#         for orderpoints_batch_ids in split_every(1000, self.ids):
#             if use_new_cursor:
#                 cr = registry(self._cr.dbname).cursor()
#                 self = self.with_env(self.env(cr=cr))
#             orderpoints_batch = self.env['stock.warehouse.orderpoint'].browse(orderpoints_batch_ids)
#             all_orderpoints_exceptions = []
#             while orderpoints_batch:
#                 procurements = []
#                 for orderpoint in orderpoints_batch:
#                     origins = orderpoint.env.context.get('origins', {}).get(orderpoint.id, False)
#                     if origins:
#                         origin = '%s - %s' % (orderpoint.display_name, ','.join(origins))
#                     else:
#                         origin = orderpoint.name
#                     if float_compare(orderpoint.qty_to_order, 0.0,
#                                      precision_rounding=orderpoint.product_uom.rounding) == 1:
#                         date = orderpoint._get_orderpoint_procurement_date()
#                         values = orderpoint._prepare_procurement_values(date=date, stock_move=stock_move)
#
#                         procurements.append(self.env['procurement.group'].Procurement(
#                             orderpoint.product_id, orderpoint.qty_to_order, orderpoint.product_uom,
#                             orderpoint.location_id, orderpoint.name, origin,
#                             orderpoint.company_id, values))
#
#                 try:
#                     with self.env.cr.savepoint():
#                         self.env['procurement.group'].with_context(from_orderpoint=True).run(procurements,
#                                                                                              raise_user_error=raise_user_error)
#                 except ProcurementException as errors:
#                     orderpoints_exceptions = []
#                     for procurement, error_msg in errors.procurement_exceptions:
#                         orderpoints_exceptions += [(procurement.values.get('orderpoint_id'), error_msg)]
#                     all_orderpoints_exceptions += orderpoints_exceptions
#                     failed_orderpoints = self.env['stock.warehouse.orderpoint'].concat(
#                         *[o[0] for o in orderpoints_exceptions])
#                     if not failed_orderpoints:
#                         _logger.error('Unable to process orderpoints')
#                         break
#                     orderpoints_batch -= failed_orderpoints
#
#                 except OperationalError:
#                     if use_new_cursor:
#                         cr.rollback()
#                         continue
#                     else:
#                         raise
#                 else:
#                     orderpoints_batch._post_process_scheduler()
#                     break
#
#             # Log an activity on product template for failed orderpoints.
#             for orderpoint, error_msg in all_orderpoints_exceptions:
#                 existing_activity = self.env['mail.activity'].search([
#                     ('res_id', '=', orderpoint.product_id.product_tmpl_id.id),
#                     ('res_model_id', '=', self.env.ref('product.model_product_template').id),
#                     ('note', '=', error_msg)])
#                 if not existing_activity:
#                     orderpoint.product_id.product_tmpl_id.activity_schedule(
#                         'mail.mail_activity_data_warning',
#                         note=error_msg,
#                         user_id=orderpoint.product_id.responsible_id.id or SUPERUSER_ID,
#                     )
#
#             if use_new_cursor:
#                 try:
#                     cr.commit()
#                 finally:
#                     cr.close()
#                 _logger.info("A batch of %d orderpoints is processed and committed", len(orderpoints_batch_ids))
#
#         return {}
#
# class StockMove(models.Model):
#     _inherit = "stock.move"
#
#     def _trigger_scheduler(self):
#         """ Check for auto-triggered orderpoints and trigger them. """
#         if not self or self.env['ir.config_parameter'].sudo().get_param('stock.no_auto_scheduler'):
#             return
#
#         orderpoints_by_company = defaultdict(lambda: self.env['stock.warehouse.orderpoint'])
#         orderpoints_context_by_company = defaultdict(dict)
#         for move in self:
#             orderpoint = self.env['stock.warehouse.orderpoint'].search([
#                 ('product_id', '=', move.product_id.id),
#                 ('trigger', '=', 'auto'),
#                 ('location_id', 'parent_of', move.location_id.id),
#                 ('company_id', '=', move.company_id.id),
#                 '!', ('location_id', 'parent_of', move.location_dest_id.id),
#             ], limit=1)
#             if orderpoint:
#                 orderpoints_by_company[orderpoint.company_id] |= orderpoint
#             if orderpoint and move.product_qty > orderpoint.product_min_qty and move.origin:
#                 orderpoints_context_by_company[orderpoint.company_id].setdefault(orderpoint.id, [])
#                 orderpoints_context_by_company[orderpoint.company_id][orderpoint.id].append(move.origin)
#         for company, orderpoints in orderpoints_by_company.items():
#             orderpoints.with_context(origins=orderpoints_context_by_company[company])._procure_orderpoint_confirm(
#                 company_id=company, raise_user_error=False, stock_move=self)
