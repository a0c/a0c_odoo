.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

=======================
Ordered Many2Many Field
=======================

Specify ``ordered=1`` in Many2many field declaration, add objects to Many2many
field in the order you need - and they will always be read back in this order.

Usage
=====

Example::

   class some_obj(models.TransientModel):

   moves = fields.Many2many('stock.move', 'some_obj_stock_move_rel', 'wiz_id', 'move_id', readonly=1, ordered=1)
       product = fields.Many2one('product.product', required=1)

       def some_method(self):
           self.moves = [(6, 0, self.moves.search([('product_id', '=', self.product.id)], order='id desc').ids)]

In the example above, all matched stock moves will be stored in ``id desc``
order. Subsequent ``self.moves`` calls will return stock moves in this order.
