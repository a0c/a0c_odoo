from openerp.tests import common


class TestProductReplace(common.TransactionCase):

    @common.at_install(False)
    @common.post_install(True)
    def test_unsupported_fields(self):
        """ checks all Product fields are supported/ignored """
        wiz = self.env['product.replace']
        unknown_fields = wiz._find_fields(wiz._product_old_vals(), wiz._supported_fields().ids)
        unsupported_fields = map(lambda x: '%s.%s' % (x.model, x.name), unknown_fields)
        self.assertFalse(unknown_fields, wiz.msg_unsupported_fields(unsupported_fields))
