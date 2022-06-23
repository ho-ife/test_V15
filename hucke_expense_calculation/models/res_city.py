from odoo import models, fields


class ResCity(models.Model):
    _name = 'res.city'
    _description = 'Res City'

    name = fields.Char(string="Name")
    country_id = fields.Many2one('res.country', string="Country")
    daily_rate_24h = fields.Float(string="Daily Rate - 24h")
    daily_rate_8h = fields.Float(string="Daily Rate - 8h")
    percentage_for_breakfast = fields.Integer(string="Percentage for Breakfast")
    percentage_for_lunch = fields.Integer(string="Percentage for Lunch")
    percentage_for_dinner = fields.Integer(string="Percentage for Dinner")
