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
from tools.translate import _
import pdb


class stock_picking(osv.osv):
    _inherit = 'stock.picking'

    def get_crossdock_location(self, cr, uid, in_move_id, out_move_id, context=None):
        """
        Returns the crossdock location to use
        """
        stock_move_obj = self.pool.get('stock.move')
        in_move = stock_move_obj.browse(cr, uid, in_move_id, context=context)
        out_move = stock_move_obj.browse(cr, uid, out_move_id, context=context)

        # If some products are already reserved, we put the new products at the same location
        already_reserved = stock_move_obj.search(cr, uid, [('move_dest_id', '=', out_move.id)], context=context)
        if already_reserved:
            crossdock_location_id = stock_move_obj.read(cr, uid, already_reserved[0], ['location_dest_id'], context=context)['location_dest_id'][0]
        # Else we pick the crossdock location of the warehouse
        else:
            crossdock_location = in_move.location_dest_id.warehouse_id.crossdock_location_id
            partner = in_move.address_id.partner_id
            # Do not forget to check chained locations !
            crossdock_location_id = self.pool.get('stock.location').chained_location_get(cr, uid, crossdock_location, partner=partner, context=context)
            if not crossdock_location_id:
                crossdock_location_id = crossdock_location.id

        return crossdock_location_id

    def action_move(self, cr, uid, ids, context=None):
        """
        Redefine test_finished to add crossdocking management
        """
        in_ids = []
        other_ids = []
        #pdb.set_trace()
        for picking_id in self.browse(cr, uid, ids, context=context):
            if picking_id.type == 'in':
                in_ids.append(picking_id.id)
            else:
                other_ids.append(picking_id.id)

        if in_ids:
            stock_move_obj = self.pool.get('stock.move')

            # We take all moves, ordered by date (default in stock.move object)
            in_move_ids = stock_move_obj.search(cr, uid, [('picking_id', 'in', in_ids), ('state', 'not in', ('done', 'cancel'))], context=context)
            for in_move in stock_move_obj.browse(cr, uid, in_move_ids, context=context):
                # Verify the product is allowed for crossdock management
                if in_move.product_id and in_move.product_id.location_type == 'crossdock':
                    if in_move.location_dest_id.warehouse_id == False:
                        raise osv.except_osv(_('Configuration error'), _('Warehouse missing on location %s' % in_move.location_dest_id.name))
                    # Verifiy if the move is already for a stock picking out
                    if in_move.move_dest_id and in_move.move_dest_id.picking_id and in_move.move_dest_id.picking_id.type == "out":
                        # Verify if location destination is already affected to crossdock
                        if in_move.move_dest_id.location_id.id != in_move.location_dest_id.warehouse_id.crossdock_location_id.id:
                            stock_move_obj.write(cr, uid, [in_move.move_dest_id.id], {'location_id': in_move.location_dest_id.warehouse_id.crossdock_location_id.id}, context=context)
                            stock_move_obj.write(cr, uid, [in_move.id], {'location_dest_id': in_move.location_dest_id.warehouse_id.crossdock_location_id.id}, context=context)
                    else:
                        # Search if we have to reserve for this product, ordered by date (default in stock.move object)
                        out_move_ids = stock_move_obj.search(cr, uid, [('picking_id.type', '=', 'out'), ('picking_id.state', 'in', ('confirmed', 'assigned')), ('state', '=', 'confirmed'), ('product_id', '=', in_move.product_id.id)], context=context)

                        # Store the current in_move quantity in a separate variable
                        in_move_quantity = in_move.product_qty

                        for out_move in stock_move_obj.browse(cr, uid, out_move_ids, context=context):
                            if not out_move.sale_line_id or (out_move.sale_line_id and out_move.sale_line_id.type == 'make_to_stock'):
                                # Retrieve the total reserved quantity
                                search_domain = [
                                    ('id', '!=', in_move.id),
                                    ('location_dest_id', 'child_of', in_move.location_dest_id.warehouse_id.lot_stock_id.id),
                                    ('move_dest_id', '=', out_move.id),
                                    ('product_id', '=', out_move.product_id.id),
                                    ('state', '=', 'assigned')
                                ]
                                reserved_stock_move_ids = stock_move_obj.search(cr, uid, search_domain, context=context)
                                reserved_stock_move_data = stock_move_obj.read(cr, uid, reserved_stock_move_ids, ['product_qty'], context=context)
                                reserved_quantity = sum([data['product_qty'] for data in reserved_stock_move_data if data['product_qty']])

                                # If all quantity is already reserved, continue to the next
                                if reserved_quantity >= out_move.product_qty:
                                    continue

                                # Retrieve the total available quantity
                                search_domain = [
                                    ('id', '!=', in_move.id),
                                    ('location_dest_id', 'child_of', in_move.location_dest_id.warehouse_id.lot_stock_id.id),
                                    ('move_dest_id', '=', False),
                                    ('product_id', '=', out_move.product_id.id),
                                    ('state', '=', 'assigned')
                                ]
                                available_stock_move_ids = stock_move_obj.search(cr, uid, search_domain, context=context)
                                available_stock_move_data = stock_move_obj.read(cr, uid, available_stock_move_ids, ['product_qty'], context=context)
                                available_quantity = sum([data['product_qty'] for data in available_stock_move_data if data['product_qty']])

                                # Sum the available and reserved quantity
                                available_quantity = available_quantity + reserved_quantity

                                # We have receipt enough product, reserve it
                                if out_move.product_qty - available_quantity <= in_move_quantity:
                                    crossdock_quantity = out_move.product_qty - available_quantity
                                    in_move_quantity = in_move_quantity - crossdock_quantity
                                    crossdock_location_id = self.get_crossdock_location(cr, uid, in_move.id, out_move.id, context=context)
                                    data = {
                                        'product_qty': crossdock_quantity,
                                        'location_dest_id': crossdock_location_id,
                                        'move_dest_id': out_move.id,
                                        'state': 'assigned',
                                    }
                                    stock_move_obj.write(cr, uid, [out_move.id], {'location_id': crossdock_location_id}, context=context)
                                    if in_move_quantity > 0:
                                        # Residual quantity, split the move
                                        new_move_id = stock_move_obj.copy(cr, uid, in_move.id, data, context=context)
                                        stock_move_obj.write(cr, uid, [in_move.id], {'product_qty': in_move_quantity}, context=context)
                                    else:
                                        # All the products are reserved, just modify the move
                                        if in_move.move_dest_id:
                                            stock_move_obj.write(cr, uid, [in_move.move_dest_id.id], {'move_dest_id': out_move.id, 'location_id': crossdock_location_id, 'location_dest_id': crossdock_location_id}, context=context)
                                            stock_move_obj.write(cr, uid, [in_move.id], {'location_dest_id': crossdock_location_id}, context=context)
                                        else:
                                            stock_move_obj.write(cr, uid, [in_move.id], data, context=context)
                                        # No more to reserve, we stop searching for this move
                                        break
                                # Check the "force reserve" boolean on the warehouse
                                elif in_move.location_dest_id.warehouse_id.force_reserve:
                                    crossdock_location_id = self.get_crossdock_location(cr, uid, in_move.id, out_move.id, context=context)
                                    stock_move_obj.write(cr, uid, [out_move.id], {'location_id': crossdock_location_id}, context=context)
                                    if in_move.move_dest_id:
                                        stock_move_obj.write(cr, uid, [in_move.move_dest_id.id], {'move_dest_id': out_move.id, 'location_id': crossdock_location_id, 'location_dest_id': crossdock_location_id}, context=context)
                                        stock_move_obj.write(cr, uid, [in_move.id], {'location_dest_id': crossdock_location_id}, context=context)
                                    else:
                                        stock_move_obj.write(cr, uid, [in_move.id], {'move_dest_id': out_move.id, 'location_dest_id': crossdock_location_id}, context=context)
                                    # No more to reserve, we stop searching for this move
                                    break
                                # Not enough for the current move and no force reserve, stop here
                                else:
                                    break

        return super(stock_picking, self).action_move(cr, uid, ids)

    def action_cancel(self, cr, uid, ids, context=None):
        """
        Unreserve all moves reserved for the canceled pickings
        """
        stock_move_obj = self.pool.get('stock.move')

        # Search canceled moves
        canceled_move_ids = stock_move_obj.search(cr, uid, [('picking_id', 'in', ids)], context=context)

        # Unreserve linked moves
        stock_move_ids = stock_move_obj.search(cr, uid, [('move_dest_id', 'in', canceled_move_ids)], context=context)
        stock_move_obj.write(cr, uid, stock_move_ids, {'move_dest_id': False}, context=context)

        return super(stock_picking, self).action_cancel(cr, uid, ids, context=context)

stock_picking()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
