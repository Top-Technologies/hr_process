# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    transfer_ids = fields.One2many('hr.transfer', 'employee_id', string='Transfers')
    transfer_count = fields.Integer(string='Transfer Count', compute='_compute_process_counts')

    promotion_ids = fields.One2many('hr.promotion', 'employee_id', string='Promotions & Demotions')
    promotion_count = fields.Integer(string='Promotion Count', compute='_compute_process_counts')

    disciplinary_ids = fields.One2many('hr.disciplinary.action', 'employee_id', string='Disciplinary Actions')
    disciplinary_count = fields.Integer(string='Disciplinary Count', compute='_compute_process_counts')

    active_disciplinary_status = fields.Selection([
        ('clean', 'Clean Record'),
        ('under_warning', 'Active Warning'),
        ('suspended', 'Suspended'),
    ], string='Disciplinary Standing', compute='_compute_disciplinary_standing', store=False)

    def _compute_process_counts(self):
        Transfer = self.env['hr.transfer']
        Promotion = self.env['hr.promotion']
        Disciplinary = self.env['hr.disciplinary.action']
        for emp in self:
            emp.transfer_count = Transfer.search_count([('employee_id', '=', emp.id)])
            emp.promotion_count = Promotion.search_count([('employee_id', '=', emp.id)])
            emp.disciplinary_count = Disciplinary.search_count([('employee_id', '=', emp.id)])

    def _compute_disciplinary_standing(self):
        today = fields.Date.today()
        for emp in self:
            active_actions = self.env['hr.disciplinary.action'].search([
                ('employee_id', '=', emp.id),
                ('state', 'in', ['decided', 'closed']),
            ])
            is_suspended = any(
                a.action_type == 'suspension' and a.suspension_start and a.suspension_end and a.suspension_start <= today <= a.suspension_end
                for a in active_actions
            )
            has_active_warning = any(
                a.action_type in ('first_written', 'second_written', 'final_written') and (not a.warning_expiry_date or a.warning_expiry_date >= today)
                for a in active_actions
            )

            if is_suspended:
                emp.active_disciplinary_status = 'suspended'
            elif has_active_warning:
                emp.active_disciplinary_status = 'under_warning'
            else:
                emp.active_disciplinary_status = 'clean'

    def action_view_transfers(self):
        self.ensure_one()
        return {
            'name': _('Employee Transfers: %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'hr.transfer',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }

    def action_view_promotions(self):
        self.ensure_one()
        return {
            'name': _('Promotions & Demotions: %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'hr.promotion',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }

    def action_view_disciplinary(self):
        self.ensure_one()
        return {
            'name': _('Disciplinary Records: %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'hr.disciplinary.action',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }
