# -*- coding: utf-8 -*-
##############################################################################
#
#    wms module for OpenERP, Agro-Business Specific extensions
#    Copyright (C) 2012 SYLEAM Info Services (<http://www.syleam.fr/>)
#              Sebastien LANGE <sebastien.lange@syleam.fr>
#
#    This file is a part of wms
#
#    wms is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    wms is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import osv
from openerp.osv import fields
import decimal_precision as dp
from datetime import date
from dateutil.rrule import MO, FR
from dateutil.relativedelta import relativedelta


class stock_to_date(osv.TransientModel):
    _name = 'stock.to.date'
    _description = 'Stock to date by product'
    _rec_name = 'product_id'

    def compute_stock_to_date(self, cr, uid, ids, context=None):
        """
        Compute total quantity on lines
        """
        product_obj = self.pool.get('product.product')
        line_obj = self.pool.get('stock.to.date.line')
        warehouse_obj = self.pool.get('stock.warehouse')
        self.write(cr, uid, ids, {'stock_to_date_line_ids': [(5,)]}, context=context)

        for wizard in self.browse(cr, uid, ids, context=context):
            warehouse_ids = []
            if not wizard.warehouse_id:
                warehouse_ids = warehouse_obj.search(cr, uid, [], context=context)
            else:
                warehouse_ids.append(wizard.warehouse_id.id)
            domain = ""
            for warehouse in warehouse_obj.browse(cr, uid, warehouse_ids, context=context):
                if domain:
                    domain += " OR"
                domain += " (parent_right <= " + str(warehouse.lot_stock_id.parent_right) + " AND parent_left >= " + str(warehouse.lot_stock_id.parent_left) + ")"
            cr.execute("""
                       WITH  location(id, parent_id) AS (
                            SELECT id, location_id FROM stock_location WHERE """ + domain + """)
                       SELECT r.date::date AS date_move, r.product_id FROM stock_move r
                         LEFT JOIN location src_loc ON (r.location_id = src_loc.id)
                         LEFT JOIN location dst_loc ON (r.location_dest_id = dst_loc.id)
                         WHERE
                              product_id = %s AND
                              state IN ('confirmed','assigned','waiting','done') AND
                              r.date::date >= %s AND r.date::date <= %s AND
                              (
                                     (src_loc.id IS NOT NULL AND dst_loc.id IS NULL) OR
                                     (src_loc.id IS NULL AND dst_loc.id IS NOT NULL)
                              )
                         GROUP BY r.date::date, product_id
                         ORDER BY r.date::date ASC
                       """,
                (
                    wizard.product_id.id,
                    wizard.date_from,
                    wizard.date_to,
                )
            )

            results = cr.fetchall()
            today = date.today().strftime('%Y-%m-%d')
            ok = False
            for result in results:
                if today in result:
                    ok = True
                    break
            if not ok:
                results.append((today, wizard.product_id.id))
            ctx_warehouse = context.copy()
            if isinstance(warehouse_ids, (int, long)):
                ctx_warehouse.update({
                    'warehouse': warehouse_ids,
                })
            elif warehouse_ids and len(warehouse_ids) == 1:
                ctx_warehouse.update({
                    'warehouse': warehouse_ids[0],
                })
            ctx_warehouse.update({
                'compute_child': True,
            })
            for date_move, product_id in sorted(results):
                ctx = ctx_warehouse.copy()
                ctx.update({
                    'to_date': date_move + ' 23:59:59',
                    'compute_child': True,
                })
                ctx2 = ctx.copy()
                ctx2.update({
                    'from_date': date_move + ' 00:00:00',
                })
                product = product_obj.browse(cr, uid, product_id, context=ctx)
                product2 = product_obj.browse(cr, uid, product_id, context=ctx2)
                line_obj.create(cr, uid, {
                    'stock_to_date_id': wizard.id,
                    'date': date_move,
                    'virtual_available': product.virtual_available,
                    'qty_available' : date_move == today and product.qty_available or 0.0,
                    'incoming_qty': product2.incoming_qty,
                    'input_qty': product_obj.get_product_available(cr, uid, [product_id], context=dict(ctx2, states=('done',), what=('in',)))[product_id],
                    'outgoing_qty': product2.outgoing_qty * -1,
                    'output_qty': abs(product_obj.get_product_available(cr, uid, [product_id], context=dict(ctx2, states=('done',), what=('out',)))[product_id]),
                    'color': date_move == today and True or False,
                }, context=context)
        return True

    def _get_orderpoint(self, cr, uid, ids, field_name, args, context=None):
        """
        Get orderpoint for this product
        """
        orderpoint_obj = self.pool.get('stock.warehouse.orderpoint')
        result = {}
        for wizard in self.browse(cr, uid, ids, context=context):
            result[wizard.id] = orderpoint_obj.search(cr, uid, [('product_id', '=', wizard.product_id.id)], context=context)
        return result

    def _get_report_stock(self, cr, uid, ids, field_name, args, context=None):
        """
        Get stock avalaible by location for this product
        """
        report_obj = self.pool.get('wms.report.stock.available')
        result = {}
        for wizard in self.browse(cr, uid, ids, context=context):
            result[wizard.id] = report_obj.search(cr, uid, [('usage', '=', 'internal'), ('product_id', '=', wizard.product_id.id)], context=context)
        return result

    _columns = {
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'uom_id': fields.related('product_id', 'uom_id', type='many2one', relation='product.uom', string='Default UoM'),
        'date_from': fields.date('Date start', required=True, help='Date start to compute stock'),
        'date_to': fields.date('Date End', required=True, help='Date end to compute stock'),
        'stock_to_date_line_ids': fields.one2many('stock.to.date.line', 'stock_to_date_id', 'Line of stock to date', readonly=True),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse', required=False),
        'orderpoint_ids': fields.function(_get_orderpoint, method=True, string='OrderPoint', type='one2many', relation='stock.warehouse.orderpoint', store=False),
        'report_stock_ids': fields.function(_get_report_stock, method=True, string='Stock Available', type='one2many', relation='wms.report.stock.available', store=False),
    }

    def default_get(self, cr, uid, fields_list, context=None):
        """
        Automatically populate fields and lines when opening the wizard from the selected stock move
        """
        if context is None:
            context = {}
        product_obj = self.pool.get('product.product')

        # Call to super for standard behaviour
        values = super(stock_to_date, self).default_get(cr, uid, fields_list, context=context)

        # Retrieve current stock move from context
        product_id = 'default_product_id' in context and context['default_product_id'] or 'active_id' in context and context['active_id'] or False
        orderpoint_obj = self.pool.get('stock.warehouse.orderpoint')
        report_obj = self.pool.get('wms.report.stock.available')
        user_obj = self.pool.get('res.users')
        user = user_obj.browse(cr, uid, uid, context=context)
        if product_id:
            product = product_obj.browse(cr, uid, product_id, context=context)

            # Initialize values
            values['product_id'] = product.id
            values['stock_to_date_line_ids'] = []
            orderpoint_ids = orderpoint_obj.search(cr, uid, [('product_id', '=', product_id)], context=context)
            values['orderpoint_ids'] = orderpoint_obj.read(cr, uid, orderpoint_ids, [], context=context)
            report_stock_ids = report_obj.search(cr, uid, [('usage', '=', 'internal'), ('product_id', '=', product_id)], context=context)
            values['report_stock_ids'] = report_obj.read(cr, uid, report_stock_ids, [], context=context)
        if user.context_stock2date_start:
            values['date_from'] = (date.today() + relativedelta(weekday=MO(user.context_stock2date_start))).strftime('%Y-%m-%d')
        if user.context_stock2date_end:
            values['date_to'] = 'default_date_to' in context and context['default_date_to'] or (date.today() + relativedelta(weekday=FR(user.context_stock2date_end))).strftime('%Y-%m-%d')
        return values


class stock_to_date_line(osv.TransientModel):
    _name = 'stock.to.date.line'
    _description = 'Lines of stock to date'
    _order = 'date asc'

    _columns = {
        'stock_to_date_id': fields.many2one('stock.to.date', 'Stock To Date'),
        'date': fields.date('Date'),
        'virtual_available': fields.float('Forecasted Qty', digits_compute=dp.get_precision('Product Unit of Measure'),
                                          help="Forecast quantity (computed as Quantity On Hand "
                                          "- Outgoing + Incoming)\n"
                                          "In a context with a single Stock Location, this includes "
                                          "goods stored in this location, or any of its children.\n"
                                          "In a context with a single Warehouse, this includes "
                                          "goods stored in the Stock Location of this Warehouse, or any "
                                          "of its children.\n"
                                          "In a context with a single Shop, this includes goods "
                                          "stored in the Stock Location of the Warehouse of this Shop, "
                                          "or any of its children.\n"
                                          "Otherwise, this includes goods stored in any Stock Location "
                                          "with 'internal' type."),
        'qty_available': fields.float('Quantity On Hand', digits_compute=dp.get_precision('Product Unit of Measure'),
                                      help="Current quantity of products.\n"
                                      "In a context with a single Stock Location, this includes "
                                      "goods stored at this Location, or any of its children.\n"
                                      "In a context with a single Warehouse, this includes "
                                      "goods stored in the Stock Location of this Warehouse, or any "
                                      "of its children.\n"
                                      "In a context with a single Shop, this includes goods "
                                      "stored in the Stock Location of the Warehouse of this Shop, "
                                      "or any of its children.\n"
                                      "Otherwise, this includes goods stored in any Stock Location "
                                      "with 'internal' type."),
        'incoming_qty': fields.float('Incoming', digits_compute=dp.get_precision('Product Unit of Measure'),
                                     help="Quantity of products that are planned to arrive.\n"
                                     "In a context with a single Stock Location, this includes "
                                     "goods arriving to this Location, or any of its children.\n"
                                     "In a context with a single Warehouse, this includes "
                                     "goods arriving to the Stock Location of this Warehouse, or "
                                     "any of its children.\n"
                                     "In a context with a single Shop, this includes goods "
                                     "arriving to the Stock Location of the Warehouse of this "
                                     "Shop, or any of its children.\n"
                                     "Otherwise, this includes goods arriving to any Stock "
                                     "Location with 'internal' type."),
        'outgoing_qty': fields.float('Outgoing', digits_compute=dp.get_precision('Product Unit of Measure'),
                                     help="Quantity of products that are planned to leave.\n"
                                     "In a context with a single Stock Location, this includes "
                                     "goods leaving this Location, or any of its children.\n"
                                     "In a context with a single Warehouse, this includes "
                                     "goods leaving the Stock Location of this Warehouse, or "
                                     "any of its children.\n"
                                     "In a context with a single Shop, this includes goods "
                                     "leaving the Stock Location of the Warehouse of this "
                                     "Shop, or any of its children.\n"
                                     "Otherwise, this includes goods leaving any Stock "
                                     "Location with 'internal' type."),
        'input_qty': fields.float('Input', digits_compute=dp.get_precision('Product Unit of Measure'),),
        'output_qty': fields.float('Output', digits_compute=dp.get_precision('Product Unit of Measure'),),
        'color': fields.boolean('Color', help='Just for show color in today'),
        'empty': fields.char(' ', size=1),
    }

    _defaults = {
        'color': False,
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
