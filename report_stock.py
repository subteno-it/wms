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


class ReportStockReal(osv.osv):
    """
    Display the stock available, per unit, production lot and tracking number
    """
    _name = 'wms.report.stock.available'
    _description = 'Stock available'
    _auto = False
    _rec_name = 'product_id'

    _columns = {
        'product_id': fields.many2one('product.product', 'Product', readonly=True),
        'uom_id': fields.many2one('product.uom', 'UOM', readonly=True),
        'prodlot_id': fields.many2one('stock.production.lot', 'Production lot', readonly=True),
        'tracking_id': fields.many2one('stock.tracking', 'Tracking', readonly=True),
        'location_id': fields.many2one('stock.location', 'Location', readonly=True),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse', readonly=True),
        'qty': fields.float('Qty', readonly=True),
    }

    def init(self, cr):
        drop_view_if_exists(cr, 'wms_report_stock_available')
        cr.execute("""
            CREATE OR REPLACE VIEW wms_report_stock_available as
            SELECT rs.id AS id,
                   rs.warehouse_id AS warehouse_id,
                   rs.location_dest_id AS location_id,
                   rs.product_id AS product_id,
                   rs.product_uom AS uom_id,
                   rs.prodlot_id AS prodlot_id,
                   rs.tracking_id AS tracking_id,
                   rs.qty AS qty
            FROM (
            SELECT  min(m0.id) as id, m0.product_id, m0.location_dest_id,
                    m0.product_uom, m0.prodlot_id, m0.tracking_id,
                    (SELECT warehouse_id
                     FROM   stock_location
                     WHERE  id=m0.location_dest_id) as warehouse_id,
                    (SELECT coalesce(sum(m11.product_qty), 0)
                     FROM   stock_move m11
                     WHERE  m11.state = m0.state
                     AND    m11.product_id = m0.product_id
                     AND    m11.prodlot_id IS NOT DISTINCT FROM m0.prodlot_id
                     AND    m11.tracking_id IS NOT DISTINCT FROM m0.tracking_id
                     AND    m11.location_dest_id = m0.location_dest_id
                     AND    m11.location_id != m0.location_dest_id
                     ) -
                    (SELECT coalesce(sum(m14.product_qty), 0)
                     FROM   stock_move m14
                     WHERE  m14.state= m0.state
                     AND    m14.product_id = m0.product_id
                     AND    m14.prodlot_id IS NOT DISTINCT FROM m0.prodlot_id
                     AND    m14.tracking_id IS NOT DISTINCT FROM m0.tracking_id
                     AND    m14.location_id = m0.location_dest_id
                     AND    m14.location_dest_id != m0.location_dest_id) as qty
            FROM   stock_move m0
            WHERE  m0.state='done'
            AND    location_dest_id in (SELECT id
                                        FROM   stock_location
                                        WHERE  usage = 'internal')
            GROUP by
                   location_dest_id,
                   m0.state,
                   m0.product_id,
                   m0.prodlot_id,
                   m0.tracking_id,
                   m0.product_uom
            ) rs
            WHERE rs.qty > 0
            ORDER BY rs.product_id
        """)

ReportStockReal()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
