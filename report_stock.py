# -*- coding: utf-8 -*-
##############################################################################
#
#    wms module for OpenERP, This module allows to manage crossdocking in warehouses
#    Copyright (C) 2011 SYLEAM (<http://www.syleam.fr/>)
#              Christophe CHAUVET <christophe.chauvet@syleam.fr>
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

from osv import osv
from osv import fields
from tools.sql import drop_view_if_exists
import decimal_precision as dp


class ReportStockReal(osv.osv):
    """
    Display the stock available, per unit, production lot and tracking number
    """
    _name = 'wms.report.stock.available'
    _description = 'Stock available'
    _auto = False
    _rec_name = 'product_id'

    USAGE_SELECTION = [
        ('supplier', 'Supplier Location'),
        ('view', 'View'),
        ('internal', 'Internal Location'),
        ('customer', 'Customer Location'),
        ('inventory', 'Inventory'),
        ('procurement', 'Procurement'),
        ('production', 'Production'),
        ('transit', 'Transit Location for Inter-Companies Transfers')
    ]

    _columns = {
        'product_id': fields.many2one('product.product', 'Product', readonly=True),
        'uom_id': fields.many2one('product.uom', 'UOM', readonly=True),
        'prodlot_id': fields.many2one('stock.production.lot', 'Production lot', readonly=True),
        'tracking_id': fields.many2one('stock.tracking', 'Tracking', readonly=True),
        'location_id': fields.many2one('stock.location', 'Location', readonly=True),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse', readonly=True),
        'usage': fields.related('location_id', 'usage', type='selection', selection=USAGE_SELECTION, string='Location Type', help='Help note'),
        'product_qty': fields.float('Quantity', digits_compute=dp.get_precision('Product UoM'), readonly=True),
    }

    def init(self, cr):
        drop_view_if_exists(cr, 'wms_report_stock_available')
        cr.execute("""
            CREATE OR REPLACE VIEW wms_report_stock_available AS (
                SELECT max(id) AS id,
                    (SELECT warehouse_id
                     FROM   stock_location
                     WHERE  id=report.location_id) AS warehouse_id,
                    location_id,
                    product_id,
                    (SELECT
                       product_template.uom_id
                     FROM
                       product_product,
                       product_template
                     WHERE
                       product_product.product_tmpl_id = product_template.id AND
                       product_product.id = report.product_id) AS uom_id,
                    prodlot_id,
                    tracking_id,
                    sum(qty) AS product_qty
                FROM (
                    SELECT -max(sm.id) AS id,
                        sm.location_id,
                        sm.product_id,
                        sm.prodlot_id,
                        sm.tracking_id,
                        -sum(sm.product_qty /uo.factor) AS qty
                    FROM stock_move as sm
                    LEFT JOIN stock_location sl
                        ON (sl.id = sm.location_id)
                    LEFT JOIN product_uom uo
                        ON (uo.id=sm.product_uom)
                    WHERE state = 'done' AND sm.location_id != sm.location_dest_id
                    GROUP BY sm.location_id, sm.product_id, sm.product_uom, sm.prodlot_id, sm.tracking_id
                    UNION ALL
                    SELECT max(sm.id) AS id,
                        sm.location_dest_id AS location_id,
                        sm.product_id,
                        sm.prodlot_id,
                        sm.tracking_id,
                        sum(sm.product_qty /uo.factor) AS qty
                    FROM stock_move AS sm
                    LEFT JOIN stock_location sl
                        ON (sl.id = sm.location_dest_id)
                    LEFT JOIN product_uom uo
                        ON (uo.id=sm.product_uom)
                    WHERE sm.state = 'done' AND sm.location_id != sm.location_dest_id
                    GROUP BY sm.location_dest_id, sm.product_id, sm.product_uom, sm.prodlot_id, sm.tracking_id
                ) AS report
                GROUP BY location_id, product_id, prodlot_id, tracking_id
                HAVING sum(qty) >0)
        """)

ReportStockReal()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
