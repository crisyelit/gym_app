# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, tools
from datetime import datetime
from . import constants


class Billing(models.Model):

    _name = "gym.billing"
    _auto = False
    _description = "Gym Billing"
    _order = 'month_code desc'

    partner_id = fields.Integer(string='Partner ID')
    partner_name = fields.Char(string='Partner Name', size=255)
    client_name = fields.Char(string='Nome', size=255)
    client_code = fields.Char(string='Código', size=50)
    client_id = fields.Many2one('gym.client', string="Nome")
    invoice_id = fields.Many2one('account.move', string="Ref. Última Fatura")
    payment_id = fields.Many2one('account.payment', string="Ref. Último Pagamento")
    payment_date = fields.Date(string="Data Pagamento")
    invoice_date_next = fields.Date(string="Próximo Pagamento", default=fields.Date.today())
    month = fields.Char(string='Mês', size=10)
    month_code = fields.Integer(string='Código do Mês')
    year = fields.Integer(string='Ano')
    current_status = fields.Selection([('REGULARIZADO', 'Regularizado'), ('IRREGULARIZADO', 'Irregularizado')], default=None,
                              string='Situação Atual', compute='_compute_current_status')

    def init(self):
        tools.drop_view_if_exists(self._cr, 'gym_billing')
        sql = ''
        for j in range(len(constants.YEARS)):
            year = constants.YEARS[j]
            for i in range(len(constants.MONTHS_PARCEL)):
                month = constants.MONTHS_PARCEL[i]
                sql += '''
                    SELECT 
                       row_number() over() as id,
                       p.id as partner_id,
                       p.name as partner_name,
                       SUBSTRING(split_part(p.name, ']', 1), 2) as client_code,
                       SUBSTRING(split_part(p.name, ']', 2), 2) as client_name,
                       (select id from gym_client where client_id =  SUBSTRING(split_part(p.name, ']', 1), 2) limit 1) as client_id,
                       (SELECT id FROM account_move i WHERE i.partner_id = p.id and move_type = 'out_invoice' and payment_state = 'paid' and invoice_date_next is not null order by id desc limit 1) as invoice_id, 
                       (SELECT name FROM account_move i WHERE i.partner_id = p.id and move_type = 'out_invoice' and payment_state = 'paid' and invoice_date_next is not null order by id desc limit 1) as invoice_name, 
                       (SELECT invoice_date_next FROM account_move i WHERE i.partner_id = p.id and move_type = 'out_invoice' and payment_state = 'paid' and invoice_date_next is not null order by id desc limit 1) as invoice_date_next,
                       
                       (SELECT payment_id FROM account_move i WHERE i.partner_id = p.id and move_type = 'entry' and ref = (SELECT name FROM account_move i WHERE i.partner_id = p.id and move_type = 'out_invoice' and payment_state = 'paid' and invoice_date_next is not null order by id desc limit 1) order by id desc limit 1) as payment_id, 
                       (SELECT name FROM account_move i WHERE i.partner_id = p.id and move_type = 'entry' and ref = (SELECT name FROM account_move i WHERE i.partner_id = p.id and move_type = 'out_invoice' and payment_state = 'paid' and invoice_date_next is not null order by id desc limit 1) order by id desc limit 1) as payment_name, 
                       (SELECT date FROM account_move i WHERE i.partner_id = p.id and move_type = 'entry' and ref = (SELECT name FROM account_move i WHERE i.partner_id = p.id and move_type = 'out_invoice' and payment_state = 'paid' and invoice_date_next is not null order by id desc limit 1) order by id desc limit 1) as payment_date,
                        
                        {month_code} as month_code,
                       '{month}' as month, 
                        {year} as year 
                    FROM res_partner p 
                    WHERE not exists (
                            SELECT l.id
                            FROM (account_move_line l inner join account_move i on i.id = l.move_id) inner join product_template pt on pt.id = l.product_id 
                            WHERE p.id = l.partner_id and pt.name = '{product_name_template}' and i.move_type = 'out_invoice' and i.payment_state = 'paid' and i.invoice_date_next is not null) 
                            and p.type = 'contact' 
                            and p.customer_rank > 0 
                            and exists (SELECT * from gym_client where client_id = SUBSTRING(split_part(p.name, ']', 1), 2) and state <> 'LEFT') 
                            and to_date(concat({year}, {month_code}),'YYYYMM') <= current_date 
                            and to_date(concat({year}, {month_code}),'YYYYMM') > (SELECT enrollment_date from gym_client where client_id = SUBSTRING(split_part(p.name, ']', 1), 2) and state <> 'LEFT' limit 1) 
                    '''.format(month_code=i+1, month=month, year=year, product_name_template=constants.PRODUCT_NAME_TEMPLATE % (month, year))
                sql += " and p.name ~ '[PRF/[0-9]{4}/[0-9]{5}]*' "
                if (i + 1) < len(constants.MONTHS_PARCEL):
                    sql += ' union all '
        sql_view = 'CREATE OR REPLACE VIEW gym_billing AS({})'.format(sql)
        print('sql_view: ', sql_view)
        self._cr.execute(sql_view)

    def action_pay(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoices',
            'res_model': 'account.move',
            'domain': [('move_type', '=', 'out_invoice')],
            'context': {'default_move_type': 'out_invoice', 'default_partner_id': self.partner_id, 'gym_app': 1},
            'view_mode': 'form',
            'target': 'current',
        }

    @api.depends('invoice_date_next')
    def _compute_current_status(self):
        current_date = datetime.today().date()
        for rec in self:
            rec.current_status = 'REGULARIZADO'
            if rec.invoice_date_next:
                aux_date = datetime.strptime(str(rec.invoice_date_next), '%Y-%m-%d').date()
                if aux_date < current_date:
                    rec.current_status = 'IRREGULARIZADO'
