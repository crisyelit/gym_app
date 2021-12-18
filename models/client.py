# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import re
from . import constants

class Client(models.Model):
    _name = "gym.client"
    # _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Gym Client"
    _order = "id desc"

    name = fields.Char(string='Nome', required=True, size=255, tracking=True)
    gender = fields.Selection([('M', 'Masculino'), ('F', 'Feminino'), ('O', 'Outro')], required=True, default=None,
                              tracking=True, string='Sexo')
    doc_type = fields.Selection(
        [('BI', 'Bilhete de Identidade'), ('CNI', 'Cartão Nacional de Identificação'), ('PASS', 'Passaporte'),
         ('TRE', 'Título de Residência Estrangeiro')],
        required=True, default=None, tracking=True, string='Doc. de Identificação')
    state = fields.Selection(
        [('DRAFT', 'Rascunho'), ('JOINED', 'Ativo'), ('BLOCKED', 'Bloqueado'), ('LEFT', 'Cancelado')], default='DRAFT',
        string="Estado", tracking=True)
    marital_status = fields.Selection(
        [('C', 'Casado (a)'), ('D', 'Divorciado (a)'), ('S', 'Solteiro (a)'), ('U', 'União de facto (a)')],
        tracking=True, string='Estado Civil')
    doc_num = fields.Char(string='Nº. Documento', required=True, tracking=True)
    birth_date = fields.Date(string="Data de Nascimento", required=True, tracking=True)
    phone = fields.Char(string='Telefone', size=15, tracking=True)
    mobile = fields.Char(string='Telemóvel', size=15, tracking=True)
    email = fields.Char(string='Email', size=100, tracking=True)
    image = fields.Binary(string="Foto do cliente")
    age = fields.Integer(string='Idade', compute='_compute_client_age')
    client_id = fields.Char(string='Código', tracking=True, help='Código gerado caso não for introduzido.')
    enrollment_date = fields.Date(string="Data de Inscrição", required=True, tracking=True, default=fields.Date.today())
    partner_id = fields.Integer(string='Partner ID')
    total_invoiced = fields.Float(string='Invoiced', compute='_compute_total_invoiced')
    currency_id = fields.Many2one('res.currency', compute='_get_company_currency', readonly=True,
                                  string="Currency", help='Utility field to express amount currency', store=False)
    # address fields
    street = fields.Char()
    street2 = fields.Char()
    zip = fields.Char(change_default=True)
    city = fields.Char()
    state_id = fields.Many2one("res.country.state", string='State', ondelete='restrict',
                               domain="[('country_id', '=?', country_id)]")
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict')
    country_code = fields.Char(related='country_id.code', string="Country Code")

    @api.depends('birth_date')
    def _compute_client_age(self):
        for rec in self:
            if rec.birth_date:
                rec.age = (datetime.today().date() - datetime.strptime(str(rec.birth_date),
                                                                       '%Y-%m-%d').date()) // timedelta(days=365)
            else:
                rec.age = 0

    def _compute_total_invoiced(self):
        for rec in self:
            partner = self.env['res.partner'].browse(rec.partner_id)
            rec.total_invoiced = partner.total_invoiced

    def _get_company_currency(self):
        for rec in self:
            partner = self.env['res.partner'].browse(rec.partner_id)
            rec.currency_id = partner.currency_id

    @api.constrains('birth_date')
    def check_age(self):
        for rec in self:
            if rec.age < 6:
                raise ValidationError(
                    "Menores que 6 anos de idade não são permitidos. Favor verificar a Data de Nascimento.")

    @api.constrains('name', 'birth_date')
    def check_unique_client(self):
        for rec in self:
            client = self.env['gym.client'].search(
                [('name', '=ilike', rec.name), ('birth_date', '=', rec.birth_date), ('id', '!=', rec.id)], limit=1)
            if client:
                raise ValidationError("O cliente <%s> já se encontra registado." % rec.name)

    @api.constrains('doc_type', 'doc_num')
    def check_name(self):
        for rec in self:
            if rec.doc_type and rec.doc_num:
                client = self.env['gym.client'].search(
                    [('doc_type', '=', rec.doc_type), ('doc_num', '=', rec.doc_num), ('id', '!=', rec.id)], limit=1)
                if client:
                    raise ValidationError(
                        "O Documento de Identificação <%s> e o Nº. Documento <%s> introduzido já existe." % (
                            rec.doc_type, rec.doc_num))

    @api.constrains('email')
    def check_email(self):
        for rec in self:
            if rec.email and re.fullmatch(constants.EMAIL_PATTERN, rec.email) is None:
                raise ValidationError("O email <%s> introduzido é inválido." % rec.email)

    @api.model
    def create(self, vals):
        if not vals.get('client_id'):
            vals['client_id'] = self.env['ir.sequence'].next_by_code('gym.client')
        partner_id = self.env['res.partner'].create({
            'name': '[' + vals['client_id'] + '] ' + vals['name'],
            'company_type': 'person',
            'phone': vals['phone'],
            'mobile': vals['mobile'],
            'email': vals['email'],
            'customer_rank': 1,
            'type': 'contact',
            'street': vals.get('street'),
            'street2': vals.get('street2'),
            'city': vals.get('city'),
            'state_id': vals.get('state_id'),
            'zip': vals.get('zip'),
            'country_id': vals.get('country_id'),
        })
        if partner_id:
            vals['partner_id'] = partner_id.id
        vals['state'] = 'JOINED'
        return super(Client, self).create(vals)

    def write(self, vals):
        if self.partner_id:
            partner_id = self.env['res.partner'].browse(self.partner_id)
            if partner_id:
                partner_id.write({
                    'name': '[' + vals.get('client_id', self.client_id) + '] ' + vals.get('name', self.name),
                    'phone': vals.get('phone', self.phone),
                    'mobile': vals.get('mobile', self.mobile),
                    'email': vals.get('email', self.email),
                    'type': 'contact',
                    'street': vals.get('street', self.street),
                    'street2': vals.get('street2', self.street2),
                    'city': vals.get('city', self.city),
                    'state_id': vals.get('state_id', self.state_id),
                    'zip': vals.get('zip', self.zip),
                    'country_id': vals.get('country_id', self.country_id),
                })
        return super(Client, self).write(vals)

    @api.onchange('name')
    def onchange_client_name(self):
        for rec in self:
            if rec.name:
                aux = str(rec.name)
                rec.name = aux.upper()

    def action_left(self):
        for rec in self:
            rec.state = 'LEFT'

    def action_join(self):
        for rec in self:
            rec.state = 'JOINED'

    def action_block(self):
        for rec in self:
            rec.state = 'BLOCKED'

    def action_open_my_invoices(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoices',
            'res_model': 'account.move',
            'domain': [('move_type', '=', 'out_invoice')],
            'context': {'search_default_partner_id': self.partner_id,'default_move_type': 'out_invoice'},
            'view_mode': 'tree,kanban,form',
            'target': 'current'
        }

    def archive_users(self):
        print('Schedule Action Entrado')