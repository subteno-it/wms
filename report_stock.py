# -*- coding: utf-8 -*-
##############################################################################
#
#    wms module for OpenERP, This module allows to manage crossdocking in warehouses
#    Copyright (C) 2011 SYLEAM (<http://www.syleam.fr/>)
#              Christophe CHAUVET <christophe.chauvet@syleam.fr>
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
from tools.sql import drop_view_if_exists
import decimal_precision as dp


class wms_report_stock_available(osv.Model):
    """
    Display the stock available, per unit, production lot
    """
    _name = 'wms.report.stock.available'
    _description = 'Stock available'
    _auto = False
    _rec_name = 'product_id'

    _columns = {
        'product_id': fields.many2one('product.product', 'Product', readonly=True),
        'uom_id': fields.many2one('product.uom', 'UOM', readonly=True),
        'prodlot_id': fields.many2one('stock.production.lot', 'Production lot', readonly=True),
        'location_id': fields.many2one('stock.location', 'Location', readonly=True),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse', readonly=True),
        'product_qty': fields.float('Quantity', digits_compute=dp.get_precision('Product UoM'), readonly=True),
        'usage': fields.char('Usage', size=16, help="""* Supplier Location: Virtual location representing the source location for products coming from your suppliers
                       \n* View: Virtual location used to create a hierarchical structures for your warehouse, aggregating its child locations ; can't directly contain products
                       \n* Internal Location: Physical locations inside your own warehouses,
                       \n* Customer Location: Virtual location representing the destination location for products sent to your customers
                       \n* Inventory: Virtual location serving as counterpart for inventory operations used to correct stock levels (Physical inventories)
                       \n* Procurement: Virtual location serving as temporary counterpart for procurement operations when the source (supplier or production) is not known yet. This location should be empty when the procurement scheduler has finished running.
                       \n* Production: Virtual counterpart location for production operations: this location consumes the raw material and produces finished products
                      """),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
    }

    def init(self, cr):
        drop_view_if_exists(cr, 'wms_report_stock_available')
        cr.execute("""
                CREATE OR REPLACE VIEW wms_report_stock_available AS (
                    SELECT  max(sub.id) AS id,
                            sl.company_id,
                            sl.warehouse_id,
                            sub.location_id,
                            sub.product_id,
                            pt.uom_id,
                            sub.prodlot_id,
                            sub.usage,
                            sum(sub.qty) AS product_qty
                    FROM (
                           SELECT   -max(sm.id) AS id,
                                    sm.location_id,
                                    sm.product_id,
                                    sm.prodlot_id,
                                    sl.usage,
                                    -sum(sm.product_qty /uo.factor) AS qty
                           FROM stock_move as sm
                           LEFT JOIN stock_location sl ON (sl.id = sm.location_id)
                           LEFT JOIN product_uom uo ON (uo.id=sm.product_uom)
                           WHERE state = 'done' AND sm.location_id != sm.location_dest_id
                           GROUP BY sm.location_id, sm.product_id, sm.product_uom, sm.prodlot_id, sl.usage
                           UNION ALL
                           SELECT   max(sm.id) AS id,
                                    sm.location_dest_id AS location_id,
                                    sm.product_id,
                                    sm.prodlot_id,
                                    sl.usage,
                                    sum(sm.product_qty /uo.factor) AS qty
                           FROM stock_move AS sm
                           LEFT JOIN stock_location sl ON (sl.id = sm.location_dest_id)
                           LEFT JOIN product_uom uo ON (uo.id=sm.product_uom)
                           WHERE sm.state = 'done' AND sm.location_id != sm.location_dest_id
                           GROUP BY sm.location_dest_id, sm.product_id, sm.product_uom, sm.prodlot_id, sl.usage
                    ) AS sub
                    LEFT JOIN stock_location sl ON sl.id = sub.location_id
                    LEFT JOIN product_product pp ON pp.id = sub.product_id
                    LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
                    GROUP BY sub.location_id, sub.product_id, sub.prodlot_id, sub.usage, sl.warehouse_id, pt.uom_id, sl.company_id
                    HAVING sum(sub.qty) > 0)
        """)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
