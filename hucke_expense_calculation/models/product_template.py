from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_verpflegungsmehraufwand = fields.Boolean(string="ist Verpflegungsmehraufwand")