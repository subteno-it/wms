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

from openerp import models, api, fields
from openerp.addons import decimal_precision as dp
from datetime import date
from dateutil.rrule import MO, FR
from dateutil.relativedelta import relativedelta


class StockToDate(models.TransientModel):
    _name = 'stock.to.date'
    _description = 'Stock to date by product'
    _rec_name = 'product_id'

    @api.multi
    def compute_stock_to_date(self):
        """
        Compute total quantity on lines
        """
        product_obj = self.env['product.product']
        line_obj = self.env['stock.to.date.line']
        warehouse_obj = self.env['stock.warehouse']
        self.write({'stock_to_date_line_ids': [(5,)]})

        for wizard in self:
            warehouses = self.env['stock.warehouse']
            if not wizard.warehouse_id:
                warehouses = warehouse_obj.search([])
            else:
                warehouses.add(wizard.warehouse_id)
            where_parts = []
            where_values = []
            for warehouse in warehouses:
                where_parts.append('(parent_right <= %s AND parent_left >= %s)')
                where_values.append(warehouse.lot_stock_id.parent_right)
                where_values.append(warehouse.lot_stock_id.parent_left)

            self.env.cr.execute("""
                       WITH  location(id, parent_id) AS (
                            SELECT id, location_id FROM stock_location WHERE %s)
                       SELECT r.date::date AS date_move, r.product_id FROM stock_move r
                         LEFT JOIN location src_loc ON (r.location_id = src_loc.id)
                         LEFT JOIN location dst_loc ON (r.location_dest_id = dst_loc.id)
                         WHERE
                              product_id = %%s AND
                              state IN ('confirmed','assigned','waiting') AND
                              r.date::date >= %%s AND r.date::date <= %%s AND
                              (
                                     (src_loc.id IS NOT NULL AND dst_loc.id IS NULL) OR
                                     (src_loc.id IS NULL AND dst_loc.id IS NOT NULL)
                              )
                         GROUP BY r.date::date, product_id
                         ORDER BY r.date::date ASC
                       """ % ' OR '.join(where_parts),
                tuple(where_values) + (
                    wizard.product_id.id,
                    wizard.date_from,
                    wizard.date_to,
                )
            )

            results = self.env.cr.fetchall()
            today = fields.Date.today()
            ok = False
            for result in results:
                if today in result:
                    ok = True
                    break
            if not ok:
                results.append((today, wizard.product_id.id))
            ctx_warehouse = self.env.context.copy()
            ctx_warehouse.update({
                'warehouse': warehouses.id,
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
                product = product_obj.with_context(ctx).browse(product_id)
                product2 = product_obj.with_context(ctx2).browse(product_id)
                line_obj.create({
                    'stock_to_date_id': wizard.id,
                    'date': date_move,
                    'virtual_available': product.virtual_available,
                    'qty_available' : date_move == today and product.qty_available or 0.0,
                    'incoming_qty': product2.incoming_qty,
                    'outgoing_qty': product2.outgoing_qty * -1,
                    'color': date_move == today and True or False,
                })
        return True

    product_id = fields.Many2one(comodel_name='product.product', string='Product', required=True)
    uom_id = fields.Many2one(related='product_id.uom_id', comodel_name='product.uom', string='Default UoM')
    date_from = fields.Date(string='Date start', required=True, help='Date start to compute stock')
    date_to = fields.Date(string='Date End', required=True, help='Date end to compute stock')
    stock_to_date_line_ids = fields.One2many(comodel_name='stock.to.date.line', inverse_name='stock_to_date_id', string='Line of stock to date', readonly=True)
    warehouse_id = fields.Many2one(comodel_name='stock.warehouse', string='Warehouse', required=False)
    orderpoint_ids = fields.Many2many(string='OrderPoint', comodel_name='stock.warehouse.orderpoint', domain="[('usage', '=', 'internal'), ('product_id', '=', product_id)]")
    quant_ids = fields.Many2many(string='Stock Available', comodel_name='stock.quant', domain="[('location_id.usage', '=', 'internal'), ('product_id', '=', product_id')]")

    @api.model
    def default_get(self, fields_list):
        """
        Automatically populate fields and lines when opening the wizard from the selected stock move
        """
        # Call to super for standard behaviour
        values = super(StockToDate, self).default_get(fields_list)

        # Retrieve current stock move from context
        product_id = 'default_product_id' in self.env.context and self.env.context['default_product_id'] or 'active_id' in self.env.context and self.env.context['active_id'] or False
        orderpoint_obj = self.env['stock.warehouse.orderpoint']
        quant_obj = self.env['stock.quant']

        if product_id:
            # Initialize values
            orderpoint_ids = orderpoint_obj.search([('product_id', '=', product_id)])
            quant_ids = quant_obj.search([('location_id.usage', '=', 'internal'), ('product_id', '=', product_id)])
            values.update(
                product_id=product_id,
                stock_to_date_line_ids=[],
                orderpoint_ids=orderpoint_obj.read(orderpoint_ids, []),
                quant_ids=quant_obj.read(quant_ids, []),
            )
        if self.env.user.context_stock2date_start:
            values['date_from'] = (date.today() + relativedelta(weekday=MO(self.env.user.context_stock2date_start))).strftime('%Y-%m-%d')
        if self.env.user.context_stock2date_end:
            values['date_to'] = 'default_date_to' in self.env.context and self.env.context['default_date_to'] or (date.today() + relativedelta(weekday=FR(self.env.user.context_stock2date_end))).strftime('%Y-%m-%d')

        return values


class stockToDateLine(models.TransientModel):
    _name = 'stock.to.date.line'
    _description = 'Lines of stock to date'
    _order = 'date asc'

    stock_to_date_id = fields.Many2one(comodel_name='stock.to.date', string='Stock To Date')
    date = fields.Date(string='Date')
    incoming_qty = fields.Float(string='Incoming', digits_compute=dp.get_precision('Product Unit of Measure'),
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
                                 "Location with 'internal' type.")
    outgoing_qty = fields.Float(string='Outgoing', digits_compute=dp.get_precision('Product Unit of Measure'),
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
                                 "Location with 'internal' type.")
    color = fields.Boolean(string='Color', default=False, help='Just for show color in today')
    empty = fields.Char(string=' ', size=1)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
