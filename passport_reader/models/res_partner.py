from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    passport_number = fields.Char(string='Passport Number')
    passport_expiration_date = fields.Date(string='Passport Expiration Date')
    passport_status = fields.Selection([
        ('valid', 'Valid'),
        ('expiring', 'Expiring'),
        ('expired', 'Expired')
    ], string='Passport Status', compute='_compute_passport_status', store=True)
    passport_history_ids = fields.One2many('passport.history', 'partner_id', string='Passport History')

    @api.depends('passport_expiration_date')
    def _compute_passport_status(self):
        today = fields.Date.today()
        for partner in self:
            status = False
            if partner.passport_expiration_date:
                delta = partner.passport_expiration_date - today
                if delta.days < 0:
                    status = 'expired'
                elif delta.days <= 360:
                    status = 'expiring'
                else:
                    status = 'valid'
            partner.passport_status = status

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            number = vals.get('passport_number')
            if number and self.search([('passport_number', '=', number)], limit=1):
                raise ValidationError(_('Ya existe un contacto con este número de pasaporte.'))
        partners = super().create(vals_list)
        return partners

    def write(self, vals):
        if 'passport_number' in vals:
            for partner in self:
                number = vals.get('passport_number')
                if number and self.env['res.partner'].search([('passport_number', '=', number), ('id', '!=', partner.id)], limit=1):
                    raise ValidationError(_('Ya existe un contacto con este número de pasaporte.'))
        # store history if number or expiration changes
        for partner in self:
            history_vals = {}
            if 'passport_number' in vals and partner.passport_number and vals.get('passport_number') != partner.passport_number:
                history_vals['old_passport_number'] = partner.passport_number
            if 'passport_expiration_date' in vals and partner.passport_expiration_date and vals.get('passport_expiration_date') != partner.passport_expiration_date:
                history_vals['old_expiration_date'] = partner.passport_expiration_date
            if history_vals:
                history_vals.update({
                    'partner_id': partner.id,
                    'user_id': self.env.user.id,
                    'date': fields.Datetime.now()
                })
                self.env['passport.history'].create(history_vals)
        return super().write(vals)
