from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp
from datetime import datetime
from odoo.exceptions import UserError, ValidationError
import pytz


class ExpenseIncludedMeal(models.Model):
    _name = 'expense.included.meal'
    _description = 'Expense Included Meal'

    date = fields.Datetime(string="Date", readonly=True)
    day = fields.Char(string="Day", readonly=True)
    breakfast_included = fields.Boolean(string="Breakfast included?")
    lunch_included = fields.Boolean(string="Lunch included?")
    dinner_included = fields.Boolean(string="Dinner included?")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.user.company_id, string="Company")
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True,
                                          help='Utility field to express amount currency')
    expense_for_day = fields.Monetary(string="Expenses for This Day", compute='_update_expense_for_day',
                                      currency_field='company_currency_id', readonly=True)
    hr_expense_id = fields.Many2one('hr.expense', string="Expense")
    breakfast_rate = fields.Float(compute='_update_expense_rate', string="Breakfast Rate", digits='Product Price')
    lunch_rate = fields.Float(compute='_update_expense_rate', string="Lunch Rate", digits='Product Price')
    dinner_rate = fields.Float(compute='_update_expense_rate', string="Dinner Rate", digits='Product Price')

    @api.depends('date', 'breakfast_included', 'lunch_included', 'dinner_included', 'hr_expense_id.travel_end',
                 'hr_expense_id.travel_begin', 'hr_expense_id.city_id')
    def _update_expense_rate(self):
        for record in self:
            daily_breakfast_24 = record.hr_expense_id.city_id.daily_rate_24h * (
                    record.hr_expense_id.city_id.percentage_for_breakfast / 100)
            daily_lunch_24 = record.hr_expense_id.city_id.daily_rate_24h * (
                    record.hr_expense_id.city_id.percentage_for_lunch / 100)
            daily_dinner_24 = record.hr_expense_id.city_id.daily_rate_24h * (
                    record.hr_expense_id.city_id.percentage_for_dinner / 100)

            record.breakfast_rate = daily_breakfast_24
            record.lunch_rate = daily_lunch_24
            record.dinner_rate = daily_dinner_24

    @api.depends('date', 'breakfast_included', 'lunch_included', 'dinner_included', 'hr_expense_id.travel_end',
                 'hr_expense_id.travel_begin', 'hr_expense_id.city_id')
    def _update_expense_for_day(self):
        for record in self:

            context = dict(self.env.context)
            current_timezone = context.get('tz') or self.env.user.tz
            if current_timezone:
                tz = pytz.timezone(current_timezone)
            else:
                raise UserError(_('Please set a timezone in user settings'))

            if record.hr_expense_id.travel_end and record.hr_expense_id.travel_begin:
                travel_end_str_tz = pytz.utc.localize(
                    datetime.strptime(str(record.hr_expense_id.travel_end), "%Y-%m-%d %H:%M:%S")).astimezone(tz)
                travel_end_str = travel_end_str_tz.strftime("%Y-%m-%d %H:%M:%S")

                travel_begin_str_tz = pytz.utc.localize(
                    datetime.strptime(str(record.hr_expense_id.travel_begin), "%Y-%m-%d %H:%M:%S")).astimezone(tz)
                travel_begin_str = travel_begin_str_tz.strftime("%Y-%m-%d %H:%M:%S")

                record_date_str = str(record.date)

                travel_end = datetime.strptime(travel_end_str, "%Y-%m-%d %H:%M:%S").date()
                travel_begin = datetime.strptime(travel_begin_str, "%Y-%m-%d %H:%M:%S").date()
                record_date = datetime.strptime(record_date_str, "%Y-%m-%d %H:%M:%S").date()

                if travel_end == travel_begin:
                    travel_end_time = datetime.strptime(travel_end_str, "%Y-%m-%d %H:%M:%S").time()
                    travel_begin_time = datetime.strptime(travel_begin_str, "%Y-%m-%d %H:%M:%S").time()
                    fmt = '%H:%M:%S'
                    diff_hours = datetime.strptime(str(travel_end_time), fmt) - datetime.strptime(str(travel_begin_time), fmt)
                    (h, m, s) = str(diff_hours).split(':')
                    result = int(h) * 3600 + int(m) * 60 + int(s)
                    if result > 28800:
                        record.expense_for_day = record.hr_expense_id.city_id.daily_rate_8h
                        if record.breakfast_included:
                            record.expense_for_day -= record.breakfast_rate
                        if record.lunch_included:
                            record.expense_for_day -= record.lunch_rate
                        if record.dinner_included:
                            record.expense_for_day -= record.dinner_rate
                        if record.expense_for_day <= 0:
                            record.expense_for_day = 0
                    else:
                        record.expense_for_day = 0
                else:

                    if record_date in [travel_end, travel_begin]:
                        record.expense_for_day = record.hr_expense_id.city_id.daily_rate_8h
                    else:
                        record.expense_for_day = record.hr_expense_id.city_id.daily_rate_24h

                    if record.breakfast_included:
                        record.expense_for_day -= record.breakfast_rate
                    if record.lunch_included:
                        record.expense_for_day -= record.lunch_rate
                    if record.dinner_included:
                        record.expense_for_day -= record.dinner_rate

                    if record.expense_for_day <= 0:
                        record.expense_for_day = 0

            else:
                record.expense_for_day = 0
