{
    'name': 'Passport Reader',
    'version': '0.1',
    'summary': 'Read passports using OCR and manage expirations',
    'category': 'Tools',
    'author': 'Example',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/passport_reader_views.xml',
        'views/res_partner_views.xml',
    ],
    'installable': True,
}
