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

from openerp import models, api, fields
from openerp.tools.sql import drop_view_if_exists
from openerp.addons import decimal_precision as dp
from collections import defaultdict


class WmsReportStockAvailable(models.Model):
    """
    Display the stock available, per unit, production lot
    """
    _name = 'wms.report.stock.available'
    _description = 'Stock available'
    _auto = False
    _rec_name = 'product_id'

    product_id = fields.Many2one(comodel_name='product.product', string='Product', readonly=True)
    uom_id = fields.Many2one(comodel_name='product.uom', string='UOM', readonly=True)
    prodlot_id = fields.Many2one(comodel_name='stock.production.lot', string='Production lot', readonly=True)
    location_id = fields.Many2one(comodel_name='stock.location', string='Location', readonly=True)
    warehouse_id = fields.Many2one(comodel_name='stock.warehouse', string='Warehouse', readonly=True)
    product_qty = fields.Float('Quantity', digits_compute=dp.get_precision('Product UoM'), readonly=True)
    product_warehouse_qty = fields.Float('Quantity on Warehouse', digits_compute=dp.get_precision('Product UoM'), readonly=True)
    usage = fields.Char('Usage', size=16, help="""* Supplier Location: Virtual location representing the source location for products coming from your suppliers
                  \n* View: Virtual location used to create a hierarchical structures for your warehouse, aggregating its child locations ; can't directly contain products
                  \n* Internal Location: Physical locations inside your own warehouses,
                  \n* Customer Location: Virtual location representing the destination location for products sent to your customers
                  \n* Inventory: Virtual location serving as counterpart for inventory operations used to correct stock levels (Physical inventories)
                  \n* Procurement: Virtual location serving as temporary counterpart for procurement operations when the source (supplier or production) is not known yet. This location should be empty when the procurement scheduler has finished running.
                  \n* Production: Virtual counterpart location for production operations: this location consumes the raw material and produces finished products
                 """)
    company_id = fields.Many2one(comodel_name='res.company', string='Company', readonly=True)

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
                            sum(sub.qty) AS product_qty,
                            0.0 as product_warehouse_qty
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

    @api.v7
    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False):
        if context is None:
            context = {}
        res = super(WmsReportStockAvailable, self).read_group(cr, uid, domain, fields, groupby, offset=offset, limit=limit, context=context, orderby=orderby)
        product_obj = self.pool.get('product.product')
        warehouse_product = defaultdict(list)
        for value in res:
            if len(value['__domain']) == 3 and value['__domain'][0][0] == 'product_id' and value['__domain'][1][0] == 'warehouse_id' and value['__domain'][2][0] == 'usage':
                warehouse_product[value['__domain'][1][2]].append(value['__domain'][0][2])
        if warehouse_product:
            for warehouse_id, product_ids in warehouse_product.items():
                res_qty = product_obj._product_available(cr, uid, product_ids, field_names=['qty_available'], context=dict(context, warehouse=warehouse_id))
                for value in res:
                    if value['__domain'][1][2] == warehouse_id:
                        value['product_warehouse_qty'] = res_qty[value['__domain'][0][2]]['qty_available']
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
