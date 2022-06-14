from odoo import models, fields


class ResCountry(models.Model):
    _inherit = 'res.country'

    daily_rate_24h = fields.Float(string="Daily Rate - 24h")
    daily_rate_8h = fields.Float(string="Daily Rate - 8h")
    percentage_for_breakfast = fields.Integer(string="Percentage for Breakfast")
    percentage_for_lunch = fields.Integer(string="Percentage for Lunch")
    percentage_for_dinner = fields.Integer(string="Percentage for Dinner")