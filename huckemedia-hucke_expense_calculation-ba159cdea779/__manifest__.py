{
    'name': 'Hucke Expense Calculation',
    'author': 'Hucke Media GmbH & Co. KG/IFE GmbH',
    'category': 'Custom',
    'website': 'https://www.hucke-media.de/',
    'licence': 'AGPL-3',
    'summary': 'Automatic calculation of expenses',
    'version': '15.0.1.0.0',
    'description': """
    Automatic calculation of expenses
    """,
    'depends': [
        'base',
        'account',
        'hr_expense',
        'sale_timesheet',
        'sale_expense',
        'product',
        'contacts',
        'l10n_de'
    ],
    'data': [
        'data/product_data.xml',
        'views/hr_expense_sheet_views.xml',
        'views/res_country_views.xml',
        'views/expense_included_meal_views.xml',
        'views/product_product_views.xml',
        'views/res_city_views.xml',

        'security/ir.model.access.csv',

        'report/report_papeformat.xml',
        'report/hr_expense_report.xml',
        'report/expense_included_meal_report.xml',
        'report/expense_included_meal.xml',
        'report/din5008_report.xml'

    ],
    'sequence': 666,
    'installable': True,
    'application': False,
}
