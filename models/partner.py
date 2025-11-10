# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.http import request
import re
import logging
import datetime

_logger = logging.getLogger(__name__)

class CustomResPartner(models.Model):
    _inherit = 'res.partner'
    
    has_license = fields.Boolean(string="Tiene licencia", default=False)
    mail_cc = fields.Char(string="CC de correo", help="Dirección de correo para CC en notificaciones")
    registration_ip = fields.Char(string="IP de registro", readonly=True)
    registration_date = fields.Datetime(string="Fecha de registro", readonly=True)
    is_verified_email = fields.Boolean(string="Email verificado", default=False)

    # Campo para identificar distribuidores
    is_distributor = fields.Boolean(
        string='Es Distribuidor',
        default=False,
        help='Marcar si este contacto es un distribuidor de máquinas'
    )
    
    # Campos para notificaciones WhatsApp
    whatsapp_phone = fields.Char(
        string='Teléfono WhatsApp',
        help='Número de teléfono para notificaciones por WhatsApp'
    )
    
    notify_new_stock = fields.Boolean(
        string='Notificar Nuevo Stock',
        default=True,
        help='Recibir notificaciones cuando lleguen nuevas máquinas'
    )
    
    notify_orders = fields.Boolean(
        string='Notificar Órdenes',
        default=True,
        help='Recibir notificaciones sobre el estado de las órdenes'
    )
    
    # Preferencias de máquinas - CORREGIDO: comentado hasta que exista el modelo
    # preferred_brands = fields.Many2many(
    #     'marcas.maquinas',
    #     string='Marcas Preferidas',
    #     help='Marcas de máquinas de interés para notificaciones'
    # )
    
    preferred_types = fields.Selection([
        ('monocroma', 'Monocroma'),
        ('color', 'Color'),
        ('both', 'Ambas')
    ], string='Tipos Preferidos', default='both',
       help='Tipos de máquinas de interés')
    
    # Campos relacionados con órdenes
    copier_order_count = fields.Integer(
        string='Órdenes de Máquinas',
        compute='_compute_copier_order_count'
    )
    
    copier_machine_count = fields.Integer(
        string='Máquinas Compradas',
        compute='_compute_copier_machine_count'
    )

    def _compute_copier_order_count(self):
        """Contar órdenes que contienen máquinas usadas"""
        for partner in self:
            # CORREGIDO: Verificar si existe sale_order_ids
            if hasattr(partner, 'sale_order_ids'):
                orders = partner.sale_order_ids.filtered(
                    lambda o: any(line.product_id.name == 'Venta de Máquina Usada' 
                                 for line in o.order_line)
                )
                partner.copier_order_count = len(orders)
            else:
                partner.copier_order_count = 0

    def _compute_copier_machine_count(self):
        """Contar máquinas compradas por este distribuidor"""
        for partner in self:
            # CORREGIDO: Verificar si existe el modelo copier.stock
            try:
                machines = self.env['copier.stock'].search([
                    ('reserved_by', '=', partner.id),
                    ('state', '=', 'sold')
                ])
                partner.copier_machine_count = len(machines)
            except:
                partner.copier_machine_count = 0

    def action_view_copier_orders(self):
        """Ver órdenes de máquinas de este distribuidor"""
        self.ensure_one()
        
        # CORREGIDO: Verificar si existe sale_order_ids
        if not hasattr(self, 'sale_order_ids'):
            return False
            
        orders = self.sale_order_ids.filtered(
            lambda o: any(line.product_id.name == 'Venta de Máquina Usada' 
                         for line in o.order_line)
        )
        
        return {
            'name': f'Órdenes de {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [('id', 'in', orders.ids)],
            'context': {'default_partner_id': self.id}
        }

    def action_view_copier_machines(self):
        """Ver máquinas compradas por este distribuidor"""
        self.ensure_one()
        
        # CORREGIDO: Verificar si existe el modelo
        try:
            return {
                'name': f'Máquinas de {self.name}',
                'type': 'ir.actions.act_window',
                'res_model': 'copier.stock',
                'view_mode': 'list,form',
                'domain': [('reserved_by', '=', self.id), ('state', '=', 'sold')],
            }
        except:
            return False
    
    @api.model_create_multi
    def create(self, vals_list):
        # Procesar cada registro en la lista
        for vals in vals_list:
            # Obtener la IP del usuario directamente del objeto request
            if hasattr(request, 'httprequest'):
                vals['registration_ip'] = request.httprequest.remote_addr
                vals['registration_date'] = fields.Datetime.now()

            # Verificar que el email sea válido
            if vals.get('email'):
                if not self._is_valid_email(vals.get('email')):
                    raise ValidationError(_("El correo electrónico no parece ser válido."))

                # Verificar que no sea un dominio de correo desechable
                if self._is_disposable_email(vals.get('email')):
                    raise ValidationError(_("No se permiten correos electrónicos temporales o desechables."))

        return super(CustomResPartner, self).create(vals_list)

    
    def _is_valid_email(self, email):
        """Verificar si el formato del correo es válido usando regex"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def _is_disposable_email(self, email):
        """Comprobar si el dominio es un proveedor de correo desechable"""
        domain = email.split('@')[-1].lower()
        disposable_domains = [
            'mailinator.com', 'yopmail.com', 'tempmail.com', 'guerrillamail.com', 
            'temp-mail.org', 'throwawaymail.com', '10minutemail.com', 'mailnesia.com',
            'trash-mail.com', 'getairmail.com', 'mailnull.com', 'spamgourmet.com',
            'sharklasers.com', 'spam4.me', 'dispostable.com', 'nada.email',
            'getnada.com', 'spamex.com', 'mytrashmail.com'
        ]
        return domain in disposable_domains
class ResUsers(models.Model):
    _inherit = 'res.users'
    
    @api.model
    def create(self, vals):
        """Sobreescribe create para agregar verificación de CAPTCHA si es necesario"""
        if not vals.get('captcha_verified', False):
            # Implementa aquí la lógica para verificar CAPTCHA
            # Esta es una implementación mock, deberías usar un servicio real como reCAPTCHA
            _logger.info("Se debería verificar CAPTCHA aquí")
            # vals['captcha_verified'] = True
        
        return super(ResUsers, self).create(vals)