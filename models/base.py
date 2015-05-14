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

from openerp import models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    context_stock2date_start = fields.Integer(string='Stock to date start', default=-1, help='Week basis for the calculation of the stock to date in relation to current week')
    context_stock2date_end = fields.Integer(string='Stock to date end', default=4, help='Last week for the calculation of the stock to date in relation to current week')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
