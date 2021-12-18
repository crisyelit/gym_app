# -*- coding: utf-8 -*-
###############################################################################
#
#    Marcel IEKINY & Others.
#    Copyright (C) 2021-TODAY IMarcelF(<http://www.imarcelf.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
{
    'name' : 'Gym App',
    'version' : '1.0',
    'summary': 'Gym Management Software',
	"author": "MARCEL IEKINY",
	'support': 'iekinyfernandes@gmail.com',
    'sequence': -100,
    'description': """Gym Management Software ... """,
    'category': 'Tutorials',
    'website': 'https://nosi.cv/',
	"development_status": "Beta",
	'license': 'LGPL-3',
    'depends' : ['account'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/data.xml',
        'views/client_view.xml',
        'views/invoice_view.xml',
        'views/payment_view.xml',
        'views/billing_view.xml',
        'views/check_in_view.xml',
        'views/settings_view.xml',
		'menus/menu.xml',
        'report/gym_client_card.xml',
        'report/reports.xml'
    ],
	'images' : [],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
