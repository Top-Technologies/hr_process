# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class HrTransfer(models.Model):
    _name = 'hr.transfer'
    _description = 'Employee Transfer'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)
    transfer_type = fields.Selection([
        ('department', 'Department Transfer'),
        ('location', 'Location / Branch Transfer'),
        ('manager', 'Reporting Line Change'),
        ('project', 'Project / Site Reassignment'),
    ], string='Transfer Type', default='department', required=True, tracking=True)

    effective_date = fields.Date(string='Effective Date', required=True, default=fields.Date.today, tracking=True)
    reason = fields.Text(string='Reason for Transfer', required=True, tracking=True)

    # Current Details (Source)
    current_department_id = fields.Many2one('hr.department', string='Current Department', readonly=True, tracking=True)
    current_job_id = fields.Many2one('hr.job', string='Current Job Position', readonly=True, tracking=True)
    current_manager_id = fields.Many2one('hr.employee', string='Current Manager', readonly=True, tracking=True)
    current_address_id = fields.Many2one('res.partner', string='Current Work Location', readonly=True)

    # Destination Details
    new_department_id = fields.Many2one('hr.department', string='New Department', tracking=True)
    new_job_id = fields.Many2one('hr.job', string='New Job Position', tracking=True)
    new_manager_id = fields.Many2one('hr.employee', string='New Manager', tracking=True)
    new_address_id = fields.Many2one('res.partner', string='New Work Location')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted to Manager'),
        ('current_approved', 'Approved by Current Manager'),
        ('receiving_approved', 'Accepted by Receiving Manager'),
        ('approved', 'Approved by HR / GM'),
        ('done', 'Transferred / Completed'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True, copy=False)

    approved_by_id = fields.Many2one('res.users', string='Approved By', readonly=True, copy=False)
    approval_date = fields.Date(string='Approval Date', readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.transfer') or _('New')
        return super().create(vals_list)

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            self.current_department_id = self.employee_id.department_id
            self.current_job_id = self.employee_id.job_id
            self.current_manager_id = self.employee_id.parent_id
            self.current_address_id = self.employee_id.address_id

    def action_submit(self):
        for rec in self:
            if not rec.employee_id:
                raise UserError(_("Please specify an employee."))
            rec.state = 'submitted'
            rec.message_post(body=_("Transfer request submitted for initial review."))

    def action_current_manager_approve(self):
        for rec in self:
            rec.state = 'current_approved'
            rec.message_post(body=_("Transfer approved by Current Manager (%s). Awaiting Receiving Manager.") % self.env.user.name)

    def action_receiving_manager_approve(self):
        for rec in self:
            rec.state = 'receiving_approved'
            rec.message_post(body=_("Transfer accepted by Receiving Manager (%s). Awaiting Final HR/GM approval.") % self.env.user.name)

    def action_approve(self):
        for rec in self:
            rec.state = 'approved'
            rec.approved_by_id = self.env.user
            rec.approval_date = fields.Date.today()
            rec.message_post(body=_("Transfer formally approved by HR / Management (%s).") % self.env.user.name)

    def action_apply_transfer(self):
        """Execute the transfer and automatically update employee profile."""
        for rec in self:
            if not rec.employee_id:
                continue
            update_vals = {}
            if rec.new_department_id:
                update_vals['department_id'] = rec.new_department_id.id
            if rec.new_job_id:
                update_vals['job_id'] = rec.new_job_id.id
            if rec.new_manager_id:
                update_vals['parent_id'] = rec.new_manager_id.id
            if rec.new_address_id:
                update_vals['address_id'] = rec.new_address_id.id

            if update_vals:
                rec.employee_id.sudo().write(update_vals)
            rec.state = 'done'
            rec.message_post(body=_("Transfer executed successfully. Employee master profile has been updated."))

    def action_reject(self):
        for rec in self:
            rec.state = 'rejected'
            rec.message_post(body=_("Transfer request has been rejected by %s.") % self.env.user.name)

    def action_reset_draft(self):
        for rec in self:
            rec.state = 'draft'
