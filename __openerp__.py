# -*- coding: utf-8 -*-
##############################################################################
#
#    wms module for OpenERP, This module allows to manage crossdocking in warehouses
#    Copyright (C) 2011 SYLEAM Info Services (<http://www.Syleam.fr/>)
#              Sylvain Garancher <sylvain.garancher@syleam.fr>
#    Copyright (C) 2013 SYLEAM Info Services (<http://www.Syleam.fr/>)
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

{
    'name': 'Warehouse Management System',
    'version': '1.2',
    'category': 'Generic Modules/Inventory Control',
    'description': """This module is extensions to stock module""",
    'author': 'SYLEAM',
    'website': 'http://www.syleam.fr/',
    'depends': [
        'base',
        'stock',
    ],
    'images': [],
    'data': [
        'security/ir.model.access.csv',
        # 'security/wms_security.xml',
        'views/base.xml',
        'views/stock.xml',
        # 'views/report_stock.xml',
        # 'wizard/stock_to_date_view.xml',
    ],
    'test': [],
    'installable': True,
    'active': False,
    'license': 'AGPL-3',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
