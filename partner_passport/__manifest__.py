{
    'name': 'Partner Passport OCR',
    'summary': 'Manage passports and OCR scanning',
    'version': '1.0',
    'author': 'Example',
    'depends': ['base'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/cron.xml',
        'views/res_partner_passport_views.xml',
    ],
    'installable': True,
}
