from odoo import fields, models

class PassportHistory(models.Model):
    _name = 'passport.history'
    _description = 'Passport History'
    _order = 'date desc'

    partner_id = fields.Many2one('res.partner', required=True, ondelete='cascade')
    old_passport_number = fields.Char()
    old_expiration_date = fields.Date()
    date = fields.Datetime(default=fields.Datetime.now)
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user)
