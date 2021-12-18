# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, tools
from odoo.exceptions import ValidationError, RedirectWarning
from datetime import datetime


class CheckIn(models.Model):

    _name = "gym.check.in"
    _description = "Gym Check In"
    _order = 'id desc'

    client_id = fields.Many2one('gym.client', string="Nome", required=True)
    client_code = fields.Char(string='Código', store=False, required=True)
    image = fields.Binary(string="Foto do cliente", store=False)
    check_in = fields.Datetime(string="Entrada", required=True)
    check_out = fields.Datetime(string="Saída")
    current_status = fields.Selection([('AUTHORIZED', 'Autorizado'), ('REFUSED', 'Recusado')],
                                      default=None,
                                      string='Situação Atual', store=False)
    name_description = fields.Char(string='Name/Description', store=False)
    last_visit = fields.Datetime(string="Última Visita", readonly=True, store=False)
    total_visit = fields.Char(string='Visita Últimos 30dias', readonly=True, store=False)


    @api.onchange('client_code')
    def onchange_client_code(self):
        for rec in self:
            if self.client_code:
                gym_client = self.env['gym.client'].search([('client_id', '=', rec.client_code)], limit=1)
                self._load_gym_client(rec, gym_client)

    @api.onchange('client_id')
    def onchange_client_id(self):
        for rec in self:
            if rec.client_id:
                self._load_gym_client(rec, rec.client_id)

    @api.constrains('client_code')
    def check_current_status(self):
        for rec in self:
            if rec.current_status != 'AUTHORIZED':
                raise ValidationError('Estado de membro inválido. Favor entrar em contacto com a Administração.')

    def action_check_in(self):
        for rec in self:
            rec.check_in = datetime.now()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Check In',
            'res_model': 'gym.check.in',
            'view_mode': 'form',
            'target': 'inline',
        }

    def action_check_out(self):
        for rec in self:
           if rec.check_out:
               raise ValidationError('Check-out já definido. Favor verificar Data/Hora saída.')
           else:
               rec.check_out = datetime.now()

    def _load_gym_client(self, rec, gym_client):
        if not gym_client:
            rec.name_description = 'Membro não encontrado. Atenção favor entrar em contacto com a Administração.'
            rec.image = None
            rec.current_status = None
            rec.client_id = None
            rec.last_visit = None
            rec.total_visit = None
            return
        if gym_client.state != 'JOINED':
            rec.name_description = 'Membro Boqueado ou Cancelado. Atenção favor entrar em contacto com a administração.'
            rec.image = None
            rec.current_status = None
            rec.client_id = None
            rec.last_visit = None
            rec.total_visit = None
            return
        rec.client_code = gym_client.client_id
        rec.client_id = gym_client.id
        rec.name_description = 'Bem-vindo, ' + gym_client.name if gym_client.gender == 'M' else 'Bem-vinda, ' + gym_client.name
        rec.image = gym_client.image
        rec.current_status = 'REFUSED'
        invoice = self.env['account.move'].search(
            [('move_type', '=', 'out_invoice'), ('partner_id', '=', gym_client.partner_id),
             ('payment_state', '=', 'paid'),
             ('invoice_date_next', '!=', False)
             ], limit=1, order='id desc')
        if invoice and invoice.invoice_date_next:
            current_date = datetime.today().date()
            aux_date = datetime.strptime(str(invoice.invoice_date_next), '%Y-%m-%d').date()
            if aux_date >= current_date:
                rec.current_status = 'AUTHORIZED'