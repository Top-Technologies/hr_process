# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class HrDisciplinaryAction(models.Model):
    _name = 'hr.disciplinary.action'
    _description = 'Employee Disciplinary Action'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)
    department_id = fields.Many2one('hr.department', string='Department', related='employee_id.department_id', store=True)
    manager_id = fields.Many2one('hr.employee', string='Direct Manager', related='employee_id.parent_id', store=True)

    incident_date = fields.Date(string='Incident Date', required=True, default=fields.Date.today, tracking=True)
    action_type = fields.Selection([
        ('verbal', 'Verbal Warning'),
        ('first_written', 'First Written Warning'),
        ('second_written', 'Second Written Warning'),
        ('final_written', 'Final Written Warning'),
        ('suspension', 'Suspension'),
        ('demotion', 'Disciplinary Demotion'),
        ('dismissal', 'Dismissal / Termination'),
    ], string='Action / Penalty Type', tracking=True)

    offense_category = fields.Selection([
        ('attendance', 'Attendance / Lateness / Absenteeism'),
        ('conduct', 'Misconduct / Insubordination'),
        ('performance', 'Poor Performance / Negligence'),
        ('policy', 'Company Policy / Safety Violation'),
        ('integrity', 'Integrity / Fraud / Theft'),
        ('other', 'Other Incident'),
    ], string='Offense Category', required=True, default='conduct', tracking=True)

    incident_description = fields.Text(string='Incident Description / Violation', required=True, tracking=True)
    employee_explanation = fields.Text(string='Employee Explanation / Defense', tracking=True)
    hearing_date = fields.Date(string='Hearing / Committee Date', tracking=True)
    hearing_findings = fields.Text(string='Investigation & Committee Findings', tracking=True)

    suspension_days = fields.Integer(string='Suspension Duration (Days)', default=0)
    suspension_start = fields.Date(string='Suspension Start Date')
    suspension_end = fields.Date(string='Suspension End Date')

    warning_validity_months = fields.Integer(string='Warning Expiry / Validity (Months)', default=6,
                                             help="Period after which the warning record is considered expired from active consideration.")
    warning_expiry_date = fields.Date(string='Warning Expiry Date', compute='_compute_warning_expiry', store=True)

    state = fields.Selection([
        ('draft', 'Incident Logged'),
        ('explanation', 'Awaiting Employee Explanation'),
        ('inquiry', 'Under Inquiry / Hearing'),
        ('decided', 'Sanction Decided / Approved'),
        ('appealed', 'Under Appeal'),
        ('closed', 'Closed / Case Concluded'),
        ('cancelled', 'Cancelled / Exonerated'),
    ], string='Status', default='draft', tracking=True, copy=False)

    sanction_approved_by = fields.Many2one('res.users', string='Sanction Approved By', readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.disciplinary.action') or _('New')
        return super().create(vals_list)

    @api.depends('incident_date', 'warning_validity_months')
    def _compute_warning_expiry(self):
        from dateutil.relativedelta import relativedelta
        for rec in self:
            if rec.incident_date and rec.warning_validity_months:
                rec.warning_expiry_date = rec.incident_date + relativedelta(months=rec.warning_validity_months)
            else:
                rec.warning_expiry_date = False

    def action_request_explanation(self):
        for rec in self:
            rec.state = 'explanation'
            rec.message_post(body=_("Explanation formally requested from employee regarding the reported incident."))

    def action_proceed_inquiry(self):
        for rec in self:
            rec.state = 'inquiry'
            rec.message_post(body=_("Explanation received. Case forwarded to Disciplinary Hearing / Committee."))

    def action_decide_sanction(self):
        for rec in self:
            if not rec.action_type:
                raise UserError(_("Please select an Action / Penalty Type before approving the sanction."))
            rec.state = 'decided'
            rec.sanction_approved_by = self.env.user
            rec.message_post(body=_("Disciplinary sanction (%s) formally approved and decided by %s.") % (
                dict(rec._fields['action_type'].selection).get(rec.action_type), self.env.user.name
            ))

    def action_close_case(self):
        for rec in self:
            rec.state = 'closed'
            rec.message_post(body=_("Disciplinary case closed and archived into employee records."))

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'
            rec.message_post(body=_("Case cancelled or employee exonerated by %s.") % self.env.user.name)

    def action_trigger_dismissal_clearance(self):
        """When action is dismissal, seamlessly initiate exit clearance."""
        self.ensure_one()
        if self.action_type != 'dismissal':
            raise UserError(_("Exit clearance can only be initiated when penalty is Dismissal / Termination."))

        if 'hr.clearance' in self.env:
            clearance = self.env['hr.clearance'].create({
                'employee_id': self.employee_id.id,
            })
            return {
                'name': _('Employee Clearance'),
                'type': 'ir.actions.act_window',
                'res_model': 'hr.clearance',
                'res_id': clearance.id,
                'view_mode': 'form',
            }

        return {
            'name': _('Employee Offboarding / Departure'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.departure.wizard',
            'views': [[False, 'form']],
            'target': 'new',
            'context': {
                'active_id': self.employee_id.id,
                'active_ids': self.employee_id.ids,
                'default_employee_id': self.employee_id.id,
            },
        }
