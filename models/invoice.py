# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
from . import constants


class Invoice(models.Model):

    _inherit = "account.move"

    invoice_date_next = fields.Date(string="Próxima Faturação")

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if not self.env.context.get('gym_app') or self.move_type != 'out_invoice':
            return
        self.invoice_line_ids = [(5, 0, 0)]
        self.write({'invoice_line_ids': [(5, 0, 0)]})
        self.invoice_date = None
        self.invoice_date_next = None
        self.invoice_date_due = None
        if self.partner_id:
            invoice = self.env['account.move'].search(
                [('move_type', '=', 'out_invoice'), ('partner_id', '=', self.partner_id.id),
                 ('payment_state', '=', 'paid'),
                 ('invoice_date_next', '!=', False)
                 ], limit=1, order='id desc')
            if invoice:
                self.invoice_date = invoice.invoice_date_next
                months = Invoice.get_months_ordered(invoice.invoice_line_ids)
                last_month = months[len(months) - 1]
                domain = []
                if last_month[0] < 12:
                    next_month_name = constants.MONTHS_PARCEL[last_month[0]]
                    domain.append(('name', '=', constants.PRODUCT_NAME_TEMPLATE % (next_month_name, last_month[2])))
                else:
                    domain.append(('name', '=', constants.PRODUCT_NAME_TEMPLATE % ('Janeiro', last_month[2] + 1)))
                product = self.env['product.template'].search(domain, limit=1)
                account_id = self.env['account.account'].search(
                    [('company_id', '=', self.company_id.id), ('code', '=', constants.ACCOUNT_CODE)], limit=1)
                val = {'product_id': product.id, 'name': product.name, 'price_unit': product.list_price,
                       'account_id': account_id.id if account_id else None}
                self.invoice_line_ids = [(5, 0, 0), (0, 0, val)]
                self._onchange_invoice_line_ids()
                self._onchange_currency()
            else:
                gym_client = self.env['gym.client'].search([('partner_id', '=', self.partner_id.id)], limit=1)
                if gym_client:
                    self.invoice_date = gym_client.enrollment_date
                    self._onchange_invoice_date()

    @api.constrains('partner_id')
    def check_partner_invoice(self):
        if not self.env.context.get('gym_app') or self.move_type != 'out_invoice':
            return
        for rec in self:
            self.check_invoice_line_ids(rec)
            self.check_valid_client(rec)
            self.check_pending_invoice(rec)
            self.check_lastest_paid_invoice(rec)
            self.check_first_invoice(rec)

    @api.constrains('invoice_date_next')
    def check_z_invoice_date_next(self):
        if not self.env.context.get('gym_app') or self.move_type != 'out_invoice':
            return
        for rec in self:
            if not rec.invoice_date_next:
                raise ValidationError("Próxima Faturação não pode ser vazio.")
            invoice_date_next = datetime.strptime(str(rec.invoice_date_next), '%Y-%m-%d').date()
            invoice_date = datetime.strptime(str(rec.invoice_date), '%Y-%m-%d').date()
            result_date = invoice_date_next - invoice_date
            months = Invoice.get_months_ordered(rec.invoice_line_ids)
            total_months = len(months) * 30
            print('total_months: ', total_months)
            if result_date.days < total_months:
                raise ValidationError('Próxima Faturação deve ser pelos menos %s dias após a Data de Fatura.' % total_months)
        #raise ValidationError("Ocorreu um erro")

    def check_valid_client(self, rec):
        if rec.partner_id:
            gym_client = self.env['gym.client'].search([('partner_id', '=', self.partner_id.id)], limit=1)
            if not gym_client:
                raise ValidationError("Cliente inválido. Favor verificar!")

    def check_pending_invoice(self, rec):
        if rec.partner_id:
            invoice = self.env['account.move'].search(
                [('move_type', '=', 'out_invoice'), ('partner_id', '=', rec.partner_id.id),
                 ('payment_state', '!=', 'paid'), ('payment_state', '!=', 'cancel'),
                 ('invoice_date_next', '!=', False), ('id', '!=', rec.id)])
            if invoice:
                raise ValidationError("Este cliente já tem uma fatura pendente. Favor verificar!")

    def check_lastest_paid_invoice(self, rec):
        if rec.partner_id:
            months = Invoice.get_months_ordered(rec.invoice_line_ids)
            for j in range(len(rec.invoice_line_ids)):
                for i in range(months[j][0], len(constants.MONTHS_PARCEL)):
                    year = rec.invoice_line_ids[j].product_id.name.split('/')[1].split(')')[0]
                    parcela = constants.PRODUCT_NAME_TEMPLATE % (constants.MONTHS_PARCEL[i], year)
                    line = self.env['account.move.line'].search(
                        [('product_id.name', '=', parcela),
                         ('move_id.move_type', '=', 'out_invoice'),
                         ('move_id.payment_state', '=', 'paid'),
                         ('partner_id', '=', rec.partner_id.id)])
                    if line:
                        raise ValidationError(
                            "Este cliente já tem pelo menos uma parcela (%s/%s) mais recente já paga. Favor verificar!" % (
                                constants.MONTHS_PARCEL[i], year))

    def check_first_invoice(self, rec):
        if rec.partner_id:
            invoice = self.env['account.move'].search(
                [('move_type', '=', 'out_invoice'), ('partner_id', '=', self.partner_id.id),
                 ('payment_state', '=', 'paid'), ('id', '!=', rec.id),
                 ('invoice_date_next', '!=', False)
                 ], limit=1)
            if not invoice:
                gym_client = self.env['gym.client'].search([('partner_id', '=', self.partner_id.id)], limit=1)
                if gym_client:
                    enrollment_date = datetime.strptime(str(gym_client.enrollment_date), '%Y-%m-%d').date()
                    months = Invoice.get_months_ordered(rec.invoice_line_ids)
                    months_filtered = filter(
                        lambda month: month[0] == enrollment_date.month and month[2] == enrollment_date.year, months)
                    months_filtered = list(months_filtered)
                    if months[0][0] != enrollment_date.month or months[0][
                        2] != enrollment_date.year or not months_filtered:
                        raise ValidationError(
                            "A primeira parcela deve ser de mês igual ao da Data de Inscrição <{}>. Favor verificar!".format(
                                enrollment_date))

    def check_invoice_line_ids(self, rec):
        if not rec.invoice_line_ids:
            raise ValidationError("Favor definir pelo menos uma linha na fatura.")
        for invoice_line_id in rec.invoice_line_ids:
            account_move_line = self.env['account.move.line'].search(
                [('partner_id.id', '=', self.partner_id.id), ('product_id.name', '=', invoice_line_id.name),
                 ('move_id.move_type', '=', 'out_invoice'), ('move_id.payment_state', '=', 'paid'),
                 ('id', '!=', invoice_line_id.id)])
            if account_move_line:
                raise ValidationError(
                    "Parcela duplicada. Este cliente já pagou esta parcela (%s)." % invoice_line_id.name)
        months = Invoice.get_months_ordered(rec.invoice_line_ids)
        self.check_duplicate_months(months)
        self.check_skipped_months(months)

    def check_duplicate_months(self, months):
        if months:
            for month in months:
                if str(months).count(month[1]) > 1:
                    raise ValidationError("Mês(es) duplicado(s). Favor verificar.")

    def check_skipped_months(self, months):
        if months:
            for i in range(1, len(months)):
                if (months[i][0] - months[i - 1][0]) > 1:
                    raise ValidationError("Mês(es) saltado(s). Favor verificar.")

    def get_months_ordered(invoice_line_ids):
        months = []
        for invoice_line_id in invoice_line_ids:
            year = int(invoice_line_id.product_id.name.split('/')[1].split(')')[0])
            if constants.MONTHS_PARCEL[0] in invoice_line_id.product_id.name:
                months.append((1, constants.MONTHS_PARCEL[0], year))
            elif constants.MONTHS_PARCEL[1] in invoice_line_id.product_id.name:
                months.append((2, constants.MONTHS_PARCEL[1], year))
            elif constants.MONTHS_PARCEL[2] in invoice_line_id.product_id.name:
                months.append((3, constants.MONTHS_PARCEL[2], year))
            elif constants.MONTHS_PARCEL[3] in invoice_line_id.product_id.name:
                months.append((4, constants.MONTHS_PARCEL[3], year))
            elif constants.MONTHS_PARCEL[4] in invoice_line_id.product_id.name:
                months.append((5, constants.MONTHS_PARCEL[4], year))
            elif constants.MONTHS_PARCEL[5] in invoice_line_id.product_id.name:
                months.append((6, constants.MONTHS_PARCEL[5], year))
            elif constants.MONTHS_PARCEL[6] in invoice_line_id.product_id.name:
                months.append((7, constants.MONTHS_PARCEL[6], year))
            elif constants.MONTHS_PARCEL[7] in invoice_line_id.product_id.name:
                months.append((8, constants.MONTHS_PARCEL[7], year))
            elif constants.MONTHS_PARCEL[8] in invoice_line_id.product_id.name:
                months.append((9, constants.MONTHS_PARCEL[8], year))
            elif constants.MONTHS_PARCEL[9] in invoice_line_id.product_id.name:
                months.append((10, constants.MONTHS_PARCEL[9], year))
            elif constants.MONTHS_PARCEL[10] in invoice_line_id.product_id.name:
                months.append((11, constants.MONTHS_PARCEL[10], year))
            elif constants.MONTHS_PARCEL[11] in invoice_line_id.product_id.name:
                months.append((12, constants.MONTHS_PARCEL[11], year))
        if months:
            months.sort(key=lambda tup: tup[0])
            months.sort(key=lambda tup: tup[2])
        return months
