# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class HrPromotion(models.Model):
    _name = 'hr.promotion'
    _description = 'Employee Promotion / Demotion'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)
    process_type = fields.Selection([
        ('promotion', 'Promotion (Upward Advancement)'),
        ('demotion', 'Demotion (Downward / Reassignment)'),
    ], string='Process Type', default='promotion', required=True, tracking=True)

    effective_date = fields.Date(string='Effective Date', required=True, default=fields.Date.today, tracking=True)
    justification = fields.Text(string='Justification / Performance Appraisal', required=True, tracking=True)

    # Current Position & Compensation
    current_job_id = fields.Many2one('hr.job', string='Current Job Position', readonly=True, tracking=True)
    current_job_title = fields.Char(string='Current Job Title', readonly=True)
    current_wage = fields.Monetary(string='Current Wage / Salary', readonly=True, currency_field='currency_id', tracking=True)
    current_department_id = fields.Many2one('hr.department', string='Current Department', readonly=True)

    # Proposed Position & Compensation
    new_job_id = fields.Many2one('hr.job', string='New Job Position', required=True, tracking=True)
    new_job_title = fields.Char(string='New Job Title', tracking=True)
    new_wage = fields.Monetary(string='New Wage / Salary', currency_field='currency_id', required=True, tracking=True)
    new_department_id = fields.Many2one('hr.department', string='New Department')
    salary_change_percentage = fields.Float(string='Salary Change (%)', compute='_compute_salary_change', store=True)

    currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id')

    state = fields.Selection([
        ('draft', 'Draft / Recommendation'),
        ('submitted', 'Submitted to HR'),
        ('hr_validated', 'Validated by HR'),
        ('approved', 'Approved by GM'),
        ('applied', 'Applied / Promoted'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True, copy=False)

    approved_by_id = fields.Many2one('res.users', string='Approved By', readonly=True, copy=False)
    approval_date = fields.Date(string='Approval Date', readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                seq_code = 'hr.promotion' if vals.get('process_type') == 'promotion' else 'hr.demotion'
                vals['name'] = self.env['ir.sequence'].next_by_code(seq_code) or _('New')
        return super().create(vals_list)

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            self.current_job_id = self.employee_id.job_id
            self.current_job_title = self.employee_id.job_title
            self.current_department_id = self.employee_id.department_id
            self.current_wage = self.employee_id.wage or 0.0
            if not self.new_department_id:
                self.new_department_id = self.employee_id.department_id

    @api.onchange('new_job_id')
    def _onchange_new_job_id(self):
        if self.new_job_id and not self.new_job_title:
            self.new_job_title = self.new_job_id.name

    @api.depends('current_wage', 'new_wage')
    def _compute_salary_change(self):
        for rec in self:
            if rec.current_wage and rec.new_wage:
                diff = rec.new_wage - rec.current_wage
                rec.salary_change_percentage = (diff / rec.current_wage) * 100.0
            else:
                rec.salary_change_percentage = 0.0

    def action_submit(self):
        for rec in self:
            rec.state = 'submitted'
            rec.message_post(body=_("Career adjustment submitted to HR for validation."))

    def action_hr_validate(self):
        for rec in self:
            rec.state = 'hr_validated'
            rec.message_post(body=_("Validated by HR (%s). Submitted for General Manager (GM) approval.") % self.env.user.name)

    def action_gm_approve(self):
        for rec in self:
            rec.state = 'approved'
            rec.approved_by_id = self.env.user
            rec.approval_date = fields.Date.today()
            rec.message_post(body=_("Approved by General Manager (%s). Ready to apply.") % self.env.user.name)

    def action_apply_career_change(self):
        """Apply new job title, position, and salary directly to employee profile and contract."""
        for rec in self:
            if not rec.employee_id:
                continue
            vals = {}
            if rec.new_job_id:
                vals['job_id'] = rec.new_job_id.id
            if rec.new_job_title:
                vals['job_title'] = rec.new_job_title
            if rec.new_department_id:
                vals['department_id'] = rec.new_department_id.id
            if rec.new_wage:
                vals['wage'] = rec.new_wage

            rec.employee_id.sudo().write(vals)
            rec.state = 'applied'
            rec.message_post(body=_("Career change applied to employee profile. Job and wage updated successfully."))

    def action_reject(self):
        for rec in self:
            rec.state = 'rejected'
            rec.message_post(body=_("Career transition request rejected by %s.") % self.env.user.name)

    def action_reset_draft(self):
        for rec in self:
            rec.state = 'draft'
