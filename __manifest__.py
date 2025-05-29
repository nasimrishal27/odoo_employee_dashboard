# -*- coding: utf-8 -*-
{
    'name': "Employee Dashboard V18",
    'version': '1.0',
    'depends': ['hr', 'hr_attendance', 'hr_holidays'],
    'author': "Suni",
    'description': """
    """,
    'data': [
        'views/employee_dashboard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'employee_dashboard/static/src/js/employee_dashboard.js',
            'employee_dashboard/static/src/xml/employee_dashboard.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
