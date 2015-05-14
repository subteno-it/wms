# -*- coding: utf-8 -*-
##############################################################################
#
#    wms module for OpenERP, This module allows to manage crossdocking in warehouses
#    Copyright (C) 2011 SYLEAM Info Services (<http://www.Syleam.fr/>)
#              Sylvain Garancher <sylvain.garancher@syleam.fr>
#              Sebastien LANGE <sebastien.lange@syleam.fr>
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

from openerp import models, fields


class StockLocationCategory(models.Model):
    _name = 'stock.location.category'
    _description = 'Category of stock location'

    name = fields.Char(size=64, required=True, help='Name of the category of stock location')
    code = fields.Char(size=64, required=True, help='Code of the category of stock location')
    active = fields.Boolean(help='This field allows to hide the category without removing it')


class StockLocation(models.Model):
    _inherit = 'stock.location'

    warehouse_id = fields.Many2one(comodel_name='stock.warehouse', string='Warehouse', help='Warehouse where is located this location')
    categ_id = fields.Many2one(comodel_name='stock.location.category', string='Category', help='Category of this location')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
