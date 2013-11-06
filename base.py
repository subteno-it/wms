# -*- coding: utf-8 -*-
##############################################################################
#
#    wms module for OpenERP, This module allows to manage crossdocking in warehouses
#    Copyright (C) 2013 SYLEAM Info Services (<Sebastien LANGE>)
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


class res_users(osv.Model):
    _inherit = 'res.users'

    _columns = {
        'context_stock2date_start': fields.integer('Stock to date start', help='Week basis for the calculation of the stock to date in relation to current week'),
        'context_stock2date_end': fields.integer('Stock to date end', help='Last week for the calculation of the stock to date in relation to current week'),
    }

    _defaults = {
        'context_stock2date_start': -1,
        'context_stock2date_end': 4,
    }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
