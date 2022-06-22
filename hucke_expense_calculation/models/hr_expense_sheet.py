from datetime import datetime, timedelta

import babel
import babel.dates
from odoo import models, fields, api, _, tools
from odoo.exceptions import UserError, ValidationError
from odoo.tools import pycompat
from odoo.tools.misc import formatLang
import pytz


def format_date(env, date, pattern=False):
    if not date:
        return ''
    try:
        return tools.format_date(env, date, date_format=pattern)
    except babel.core.UnknownLocaleError:
        return date


def format_tz(env, dt, tz=False, format=False):
    record_user_timestamp = env.user.sudo().with_context(tz=tz or env.user.sudo().tz or 'UTC')
    timestamp = datetime.strptime(dt, tools.DEFAULT_SERVER_DATETIME_FORMAT)

    ts = fields.Datetime.context_timestamp(record_user_timestamp, timestamp)
    if env.context.get('use_babel'):
        from babel.dates import format_datetime
        return format_datetime(dt, format or 'medium', locale=env.context.get("lang") or 'en_US')

    if format:
        return pycompat.text_type(ts.strftime(format))
    else:
        lang = env.context.get("lang")
        langs = env['res.lang']
        if lang:
            langs = env['res.lang'].search([("code", "=", lang)])
        format_date = langs.date_format or '%B-%d-%Y'
        format_time = '%I:%M %p'

        fdate = pycompat.text_type(ts.strftime(format_date))
        ftime = pycompat.text_type(ts.strftime(format_time))
        return u"%s %s%s" % (fdate, ftime, (u' (%s)' % tz) if tz else u'')


class HrExpense(models.Model):
    _inherit = 'hr.expense'

    travel_begin = fields.Datetime(string="Travel Begin")
    travel_end = fields.Datetime(string="Travel End")
    customer_id = fields.Many2one('res.partner', string="Customer")
    country_id = fields.Many2one('res.country', string="Country", related='customer_id.country_id', readonly=True)
    city_id = fields.Many2one('res.city', string="City")
    number_of_days = fields.Integer(string="Number of whole days")
    number_of_travel_days = fields.Integer(string="Number of travel days")
    expense_included_meals_ids = fields.One2many('expense.included.meal', 'hr_expense_id', string="Included Meals")
    is_verpflegungsmehraufwand = fields.Boolean(related='product_id.is_verpflegungsmehraufwand',
                                                string="ist Verpflegungsmehraufwand", readonly=True)
    details = fields.Text(string="Details")

    def _fill_expense_description(self):
        context = dict(self.env.context)
        current_timezone = context.get('tz') or self.env.user.tz
        if current_timezone:
            tz = pytz.timezone(current_timezone)
        else:
            raise UserError(_('Please set a timezone in user settings'))
        if self.customer_id:
            customer_id = self.customer_id
            currency = self.currency_id.symbol

            travel_begin = format_tz(self.env, self.travel_begin, tz=tz, format=False)
            travel_end = format_tz(self.env, self.travel_end, tz=tz, format=False)

            description = ""
            description += str(self.product_id.name) + '\n'
            description += '\n' + _('Travel Begin : ') + travel_begin
            description += '\n' + _('Travel End : ') + travel_end

            if customer_id:
                description += '\n' + '\n' + _("Destination : ") + '\n' + str(customer_id.name) + '\n'
                if customer_id.street:
                    description += str(customer_id.street) + '\n'
                if customer_id.street2:
                    description += str(customer_id.street2) + '\n'
                if customer_id.zip and customer_id.city:
                    description += str(customer_id.city) + '\n'
                if customer_id.country_id:
                    description += str(customer_id.country_id.name) + '\n'

            for expense_meal in self.expense_included_meals_ids:
                description += _('\n Expense for ') + format_date(self.env, expense_meal.date, False)
                description += ' : ' + formatLang(self.env, expense_meal.expense_for_day,
                                                  digits=2) + ' ' + currency + '\n'

                time1 = datetime.strptime(self.travel_end, "%Y-%m-%d %H:%M:%S").date()
                time2 = datetime.strptime(self.travel_begin, "%Y-%m-%d %H:%M:%S").date()

                if expense_meal.date in [str(time1), str(time2)]:
                    if self.city_id:
                        description += formatLang(self.env, self.city_id.daily_rate_8h,
                                                  digits=2) + ' ' + currency + '\n'
                    else:
                        description += formatLang(self.env, self.country_id.daily_rate_8h,
                                                  digits=2) + ' ' + currency + '\n'
                else:
                    if self.city_id:
                        description += formatLang(self.env, self.country_id.daily_rate_24h,
                                                  digits=2) + ' ' + currency + '\n'
                    else:
                        description += formatLang(self.env, self.city_id.daily_rate_24h,
                                                  digits=2) + ' ' + currency + '\n'

                if expense_meal.breakfast_included:
                    description += _("- Breakfast Expense: ")
                    description += formatLang(self.env, -expense_meal.breakfast_rate,
                                              digits=2) + '' + currency + '\n'
                if expense_meal.lunch_included:
                    description += _("- Lunch Expense: ")
                    description += formatLang(self.env, -expense_meal.lunch_rate, digits=2) + ' ' + currency + '\n'
                if expense_meal.dinner_included:
                    description += _("- Dinner Expense: ")
                    description += formatLang(self.env, -expense_meal.dinner_rate, digits=2) + ' ' + currency + '\n'

            self.details = description

    @api.onchange('travel_begin', 'travel_end')
    def _calculate_number_of_travel_days(self):

        context = dict(self.env.context)
        current_timezone = context.get('tz') or self.env.user.tz
        if current_timezone:
            tz = pytz.timezone(current_timezone)
        else:
            raise UserError(_('Please set a timezone in user settings'))
        for record in self:
            if record.travel_begin and record.travel_end:
                travel_end_str_tz = pytz.utc.localize(
                    datetime.strptime(str(record.travel_end), "%Y-%m-%d %H:%M:%S")).astimezone(tz)
                travel_end_str = travel_end_str_tz.strftime("%Y-%m-%d %H:%M:%S")

                travel_begin_str_tz = pytz.utc.localize(
                    datetime.strptime(str(record.travel_begin), "%Y-%m-%d %H:%M:%S")).astimezone(tz)
                travel_begin_str = travel_begin_str_tz.strftime("%Y-%m-%d %H:%M:%S")

                record.date = travel_end_str

                travel_end = datetime.strptime(travel_end_str, "%Y-%m-%d %H:%M:%S").date()

                travel_begin = datetime.strptime(travel_begin_str, "%Y-%m-%d %H:%M:%S").date()

                if travel_begin > travel_end:
                    raise ValidationError(
                        _("The date range is not a valid (%s > %s) , please check the dates again") % (
                            record.travel_begin, record.travel_end))
                if travel_begin == travel_end:
                    travel_end_time = datetime.strptime(str(record.travel_end), "%Y-%m-%d %H:%M:%S").time()
                    travel_begin_time = datetime.strptime(str(record.travel_begin), "%Y-%m-%d %H:%M:%S").time()

                    fmt = '%H:%M:%S'
                    diff_hours = datetime.strptime(str(travel_end_time), fmt) - datetime.strptime(
                        str(travel_begin_time), fmt)
                    (h, m, s) = str(diff_hours).split(':')
                    result = int(h) * 3600 + int(m) * 60 + int(s)
                    if result > 28800:
                        record.number_of_days = 0
                        record.number_of_travel_days = 1
                    else:
                        record.number_of_days = 0
                        record.number_of_travel_days = 0

                if travel_begin < travel_end:
                    travel_sub = travel_end - travel_begin
                    if int(travel_sub.total_seconds()) <= 86400:
                        record.number_of_days = 0
                        record.number_of_travel_days = 2
                    else:
                        # Adding start day
                        subs_seconds = travel_sub.total_seconds() + 86400
                        seconds_2_days = subs_seconds / (24 * 60 * 60)
                        total_days = int(seconds_2_days)
                        record.number_of_days = total_days - 2
                        if record.number_of_days < 1:
                            record.number_of_travel_days = 0
                        else:
                            record.number_of_travel_days = 2

    @api.model
    def create(self, vals):
        context = dict(self.env.context)
        current_timezone = context.get('tz') or self.env.user.tz
        if current_timezone:
            tz = pytz.timezone(current_timezone)
        else:
            raise UserError(_('Please set a timezone in user settings'))
        res = super(HrExpense, self).create(vals)
        if res.is_verpflegungsmehraufwand:
            lang_code = self.env.context.get('lang') or self.env.user.lang or 'en_US'

            if not res.travel_begin or not res.travel_end:
                raise ValidationError(_("Please select travel information!"))

            travel_end_tz = pytz.utc.localize(
                datetime.strptime(str(res.travel_end), "%Y-%m-%d %H:%M:%S")).astimezone(tz)
            travel_end_str = travel_end_tz.strftime("%Y-%m-%d %H:%M:%S")

            travel_begin_tz = pytz.utc.localize(
                datetime.strptime(str(res.travel_begin), "%Y-%m-%d %H:%M:%S")).astimezone(tz)
            travel_begin_str = travel_begin_tz.strftime("%Y-%m-%d %H:%M:%S")

            travel_end = datetime.strptime(travel_end_str, "%Y-%m-%d %H:%M:%S").date()
            travel_begin = datetime.strptime(travel_begin_str, "%Y-%m-%d %H:%M:%S").date()

            travel_sub = travel_end - travel_begin
            number_of_seconds = int(travel_sub.total_seconds()) + 86400
            number_of_days = number_of_seconds / (24 * 60 * 60)
            for n in range(int(number_of_days)):
                date_ds = travel_begin + timedelta(n)
                self.env['expense.included.meal'].create({
                    'day': babel.dates.get_day_names('wide', locale=lang_code)[date_ds.weekday()],
                    'date': date_ds.strftime("%Y-%m-%d %H:%M:%S"),
                    'hr_expense_id': res.id
                })
            res.unit_amount = res.total_amount
        return res

    def write(self, vals):
        for record in self:
            lang_code = self.env.context.get('lang') or self.env.user.lang or 'en_US'
            context = dict(self.env.context)
            current_timezone = context.get('tz') or self.env.user.tz
            if current_timezone:
                tz = pytz.timezone(current_timezone)
            else:
                raise UserError(_('Please set a timezone in user settings'))
            if 'travel_begin' in vals and 'travel_end' in vals:
                self.env['expense.included.meal'].search([('hr_expense_id', '=', record.id)]).unlink()
                travel_end_tz = pytz.utc.localize(
                    datetime.strptime(str(vals.get('travel_end')), "%Y-%m-%d %H:%M:%S")).astimezone(tz)
                travel_end_str = travel_end_tz.strftime("%Y-%m-%d %H:%M:%S")

                travel_begin_tz = pytz.utc.localize(
                    datetime.strptime(str(vals.get('travel_begin')), "%Y-%m-%d %H:%M:%S")).astimezone(tz)
                travel_begin_str = travel_begin_tz.strftime("%Y-%m-%d %H:%M:%S")

                travel_end = datetime.strptime(travel_end_str, "%Y-%m-%d %H:%M:%S").date()
                travel_begin = datetime.strptime(travel_begin_str, "%Y-%m-%d %H:%M:%S").date()

                travel_sub = travel_end - travel_begin
                number_of_seconds = int(travel_sub.total_seconds()) + 86400
                number_of_days = number_of_seconds / (24 * 60 * 60)
                for num in range(int(number_of_days)):
                    date_dl = datetime.strptime(str(travel_begin), "%Y-%m-%d") + timedelta(num)
                    self.env['expense.included.meal'].create({
                        'day': babel.dates.get_day_names('wide', locale=lang_code)[date_dl.weekday()],
                        'date': date_dl.strftime("%Y-%m-%d %H:%M:%S"),
                        'hr_expense_id': record.id
                    })
            if 'travel_begin' in vals and 'travel_end' not in vals:
                self.env['expense.included.meal'].search([('hr_expense_id', '=', record.id)]).unlink()

                travel_end_tz = pytz.utc.localize(
                    datetime.strptime(str(record.travel_end), "%Y-%m-%d %H:%M:%S")).astimezone(tz)
                travel_end_str = travel_end_tz.strftime("%Y-%m-%d %H:%M:%S")

                travel_begin_tz = pytz.utc.localize(
                    datetime.strptime(str(vals.get('travel_begin')), "%Y-%m-%d %H:%M:%S")).astimezone(tz)
                travel_begin_str = travel_begin_tz.strftime("%Y-%m-%d %H:%M:%S")

                travel_end = datetime.strptime(travel_end_str, "%Y-%m-%d %H:%M:%S").date()
                travel_begin = datetime.strptime(travel_begin_str, "%Y-%m-%d %H:%M:%S").date()

                travel_sub = travel_end - travel_begin
                number_of_seconds = int(travel_sub.total_seconds()) + 86400
                number_of_days = number_of_seconds / (24 * 60 * 60)

                for num in range(int(number_of_days)):
                    date_dl = datetime.strptime(travel_begin_str, "%Y-%m-%d %H:%M:%S") + timedelta(num)
                    self.env['expense.included.meal'].create({
                        'day': babel.dates.get_day_names('wide', locale=lang_code)[date_dl.weekday()],
                        'date': date_dl.strftime("%Y-%m-%d %H:%M:%S"),
                        'hr_expense_id': record.id
                    })
            if 'travel_end' in vals and 'travel_begin' not in vals:
                self.env['expense.included.meal'].search([('hr_expense_id', '=', record.id)]).unlink()

                travel_end_tz = pytz.utc.localize(
                    datetime.strptime(str(vals.get('travel_end')), "%Y-%m-%d %H:%M:%S")).astimezone(tz)
                travel_end_str = travel_end_tz.strftime("%Y-%m-%d %H:%M:%S")

                travel_begin_tz = pytz.utc.localize(
                    datetime.strptime(str(record.travel_begin), "%Y-%m-%d %H:%M:%S")).astimezone(tz)
                travel_begin_str = travel_begin_tz.strftime("%Y-%m-%d %H:%M:%S")

                travel_end = datetime.strptime(travel_end_str, "%Y-%m-%d %H:%M:%S").date()
                travel_begin = datetime.strptime(travel_begin_str, "%Y-%m-%d %H:%M:%S").date()

                travel_sub = travel_end - travel_begin
                number_of_seconds = int(travel_sub.total_seconds()) + 86400
                number_of_days = number_of_seconds / (24 * 60 * 60)

                for num in range(int(number_of_days)):
                    date_dl = travel_begin + timedelta(num)
                    self.env['expense.included.meal'].create({
                        'day': babel.dates.get_day_names('wide', locale=lang_code)[date_dl.weekday()],
                        'date': date_dl.strftime("%Y-%m-%d %H:%M:%S"),
                        'hr_expense_id': record.id
                    })

        return super(HrExpense, self).write(vals)

    @api.depends('quantity', 'unit_amount', 'tax_ids', 'currency_id', 'expense_included_meals_ids.expense_for_day')
    def _compute_amount(self):
        for expense in self:
            expense.untaxed_amount = expense.unit_amount * expense.quantity
            taxes = expense.tax_ids.compute_all(expense.unit_amount, expense.currency_id, expense.quantity,
                                                expense.product_id, expense.employee_id.user_id.partner_id)
            expense.total_amount = taxes.get('total_included')

            if expense.is_verpflegungsmehraufwand and expense.expense_included_meals_ids:
                expense.total_amount = sum(expense.expense_included_meals_ids.mapped('expense_for_day'))
                expense.unit_amount = sum(expense.expense_included_meals_ids.mapped('expense_for_day'))

    def submit_expenses(self):
        if any(expense.state != 'draft' for expense in self):
            raise UserError(_("You cannot report twice the same line!"))
        if len(self.mapped('employee_id')) != 1:
            raise UserError(_("You cannot report expenses for different employees in the same report!"))
        self._fill_expense_description()
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'hr.expense.sheet',
            'target': 'current',
            'context': {
                'default_expense_line_ids': [line.id for line in self],
                'default_employee_id': self[0].employee_id.id,
                'default_name': self[0].name if len(self.ids) == 1 else '',
            }
        }

    @api.onchange('customer_id')
    def onchange_partner(self):
        for record in self:
            if record.customer_id:
                customer_city = record.customer_id.city
                cities = self.env['res.city'].search([('country_id', '=', record.country_id.id)])
                if cities:
                    city = cities.filtered(lambda m: m.id and m.name == customer_city)
                    if city:
                        record.city_id = city
                    else:
                        all_other_cities = cities.filtered(lambda m: m.id and m.name == 'all other Cities')
                        if not all_other_cities:
                            record.city_id = cities.filtered(lambda m: m.id and m.name == False)
                        else:
                            record.city_id = all_other_cities

    def action_print(self):
        self.ensure_one()
        return self.env.ref('hucke_expense_calculation.action_report_expense_included_meal').report_action(self)
