# -*- coding: utf-8 -*-
##############################################################################
#
#    wms module for OpenERP, This module allows to manage crossdocking in warehouses
#    Copyright (C) 2011 SYLEAM Info Services (<http://www.Syleam.fr/>)
#              Sylvain Garancher <sylvain.garancher@syleam.fr>
#
#    This file is a part of wms
#
#    wms is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    wms is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import osv
from osv import fields


class stock_warehouse(osv.osv):
    _inherit = 'stock.warehouse'

    _columns = {
        'force_reserve': fields.boolean('Force reserve', help='If checked, the products will be reserved, even if we need more than the available quantity'),
        'crossdock_location_id': fields.many2one('stock.location', 'Crossdock location', help='Crossdock location for this product'),
    }

stock_warehouse()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
