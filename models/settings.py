# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, tools


class GymAppSettings(models.TransientModel):

    _inherit = "res.config.settings"

    note = fields.Char(string="Default Note")

    def set_values(self):
        res = super(GymAppSettings, self).set_values()
        self.env['ir.config_parameter'].set_param('gym_app.note', self.note)
        return res

    @api.model
    def get_values(self):
        res = super(GymAppSettings, self).get_values()
        note = self.env['ir.config_parameter'].sudo().get_param('gym_app.note')
        res.update(note=note)
        return res