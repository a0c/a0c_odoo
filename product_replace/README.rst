.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

=======================================================================
Product Replace - Replace a product with another one in various objects
=======================================================================

View all usages of a product and replace the product in these usage objects
with another product. This allows to safely delete the old product afterwards
with the help of ``Delete Old Product`` button.

Two simple heuristics built into 3 buttons help finding potential duplicate
products:

- **Suggest Next Pair of Duplicates** button finds Old+New product pairs (e.g.
  ``[DPM465@-A] DPM465@-A`` and ``[4982012823197] DPM465@-A``) where Old
  product has Name = Internal Reference (indicates a possible duplicate) and
  New product has the same Name, but a different Internal Reference - that is
  probably a correct original product.

- **<< Previous Name=Code** and **Next Name=Code >>** buttons iterate
  over products with Name = Internal Reference. Such products are likely to
  have duplicates too.

For Developers
==============

Products get replaced in pure SQL to avoid potentially harmful side-effects
of onchanges and ORM writes. It is the task of ``replace()`` method to
safely imitate onchanges and ORM writes by manually updating all the related
fields normally set by onchanges and ORM writes (e.g. Stock Move's ``name``
field typically contains product's name - see it updated in module
``product_replace_stock``). Once properly updated in ``replace()``
method, the field should be made returned by ``_supported_fields()`` method
to be effectively marked as Supported field and to no longer appear in the
list of ``Unsupported Fields with References to Old Product``.

If overriding ``replace()`` method, do add the ``@audit`` decorator to it and
make it the last decorator if there are several, and pass ``no_audit=1`` to
context to only allow the topmost overriding method to handle auditing::

    @api.multi
    @audit
    def replace(self):
        super(product_replace, self.with_context(no_audit=1)).replace()
        ...
