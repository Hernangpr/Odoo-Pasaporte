import base64
import io
import re

from datetime import date

from PIL import Image, ImageOps, ImageEnhance
import pytesseract

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    passport_id = fields.Many2one('res.partner.passport', string='Passport')


class ResPartnerPassport(models.Model):
    """Passport model with OCR support and expiry checks."""

    _name = 'res.partner.passport'
    _description = 'Partner Passport'

    partner_id = fields.Many2one('res.partner', required=True, ondelete='cascade')
    number = fields.Char(string='Passport Number')
    issue_date = fields.Date()
    expiry_date = fields.Date()
    image = fields.Binary(string='Passport Image')
    state = fields.Selection([
        ('active', 'Active'),
        ('archived', 'Archived')
    ], default='active')

    # Link back to partner for easy access
    passport_ref = fields.One2many('res.partner', 'passport_id', string='Partners')

    _sql_constraints = [
        ('number_unique', 'unique(number)', 'Passport number must be unique!'),
    ]

    def _preprocess_image(self, img_data):
        """Prepare image for OCR using grayscale, contrast and threshold."""
        image = Image.open(io.BytesIO(base64.b64decode(img_data)))
        gray = ImageOps.grayscale(image)
        contrast = ImageEnhance.Contrast(gray).enhance(2.0)
        thresh = contrast.point(lambda p: 255 if p > 128 else 0)
        return thresh

    def _extract_mrz(self, text):
        lines = [l for l in text.splitlines() if len(l) > 40]
        if len(lines) >= 2:
            mrz = ''.join(lines[-2:])
            return mrz
        return ''

    def _parse_mrz(self, mrz):
        """Parse MRZ string using simple regex to fetch number and dates."""
        match = re.search(r'([A-Z0-9<]{9})(\d{6})(\d{6})', mrz)
        if not match:
            return {}
        number = match.group(1).replace('<', '')
        issue = match.group(2)
        expiry = match.group(3)
        def _fmt(date_str):
            year = int(date_str[:2])
            year += 2000 if year < 70 else 1900
            return date(year, int(date_str[2:4]), int(date_str[4:6]))
        return {
            'number': number,
            'issue_date': _fmt(issue),
            'expiry_date': _fmt(expiry),
        }

    def action_scan_passport(self):
        """Run OCR on stored passport image and fill fields."""
        for passport in self:
            if not passport.image:
                raise UserError(_('No image attached to this passport.'))
            img = passport._preprocess_image(passport.image)
            text = pytesseract.image_to_string(img, lang='eng+fra+spa')
            mrz = passport._extract_mrz(text)
            data = passport._parse_mrz(mrz)
            for key, value in data.items():
                passport[key] = value

    @api.constrains('expiry_date')
    def _check_expiry_date(self):
        for rec in self:
            if rec.expiry_date and rec.expiry_date < fields.Date.today():
                rec.partner_id.message_post(body=_('Passport expired on %s') % rec.expiry_date)

    def _cron_check_passport_expiry(self):
        """Daily job to notify about passports nearing expiration."""
        today = fields.Date.today()
        for passport in self.search([('state', '=', 'active'), ('expiry_date', '!=', False)]):
            delta = (passport.expiry_date - today).days
            if delta < 0:
                tag = 'Pasaporte vencido'
            elif delta <= 30:
                tag = 'Pasaporte por vencer (30 d\xedas)'
            elif delta <= 90:
                tag = 'Pasaporte por vencer (90 d\xedas)'
            elif delta <= 180:
                tag = 'Pasaporte por vencer (180 d\xedas)'
            elif delta <= 360:
                tag = 'Pasaporte por vencer (360 d\xedas)'
            else:
                tag = False
            if tag:
                passport.partner_id.message_post(body=_(tag))


class TravelTrip(models.Model):
    """Sample trip model to demonstrate warnings when adding passengers."""

    _name = 'travel.trip'
    _description = 'Travel Trip'

    name = fields.Char(required=True)
    partner_ids = fields.Many2many('res.partner')

    @api.constrains('partner_ids')
    def _check_partner_passports(self):
        for trip in self:
            expired = trip.partner_ids.filtered(
                lambda p: p.passport_id and p.passport_id.expiry_date and p.passport_id.expiry_date < fields.Date.today()
            )
            if expired:
                names = ', '.join(expired.mapped('name'))
                raise ValidationError(_(
                    'These partners have expired passports: %s. Please update before confirming the trip.'
                ) % names)
