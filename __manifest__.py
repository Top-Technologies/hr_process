# -*- coding: utf-8 -*-
{
    'name': 'HR Process: Employee Career & Lifecycle Management',
    'version': '19.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Employee Transfers, Promotions, Demotions, and Disciplinary Actions',
    'description': """
HR Process & Employee Lifecycle Management
==========================================
Comprehensive module managing employee career transitions and internal HR processes:

1. **Employee Transfers (`hr.transfer`)**:
   - Internal transfers across departments, branches/locations, job positions, and reporting managers.
   - Dual-manager approval workflow (Current Manager -> Receiving Manager -> HR / GM).
   - Automatic execution on approval: auto-updates department, manager, and position on employee profile.

2. **Promotions & Demotions (`hr.promotion`)**:
   - Manages upward promotion and downward demotion processes.
   - Tracks previous vs. new job positions, salary/wage adjustments, grade levels, and justifications.
   - Multi-step approval (Recommendation -> HR Validation -> GM Approval).
   - Automatic execution on approval: applies new job position, title, and salary to employee contract.

3. **Disciplinary Actions (`hr.disciplinary.action`)**:
   - Manages formal disciplinary procedures (Verbal/Written Warnings, Suspensions, Demotions, Dismissals).
   - Inquiry lifecycle: incident logging, employee explanation, committee findings, and sanction enforcement.
   - Active disciplinary badge on employee profile.
   - Seamless linkage to employee exit clearance upon dismissal.

4. **Employee Profile Integration**:
   - Career history timeline and smart buttons on `hr.employee`.
    """,
    'author': 'Top Technologies',
    'website': 'https://toptechnologies.et',
    'license': 'LGPL-3',
    'depends': [
        'hr',
        'mail',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'security/record_rules.xml',
        'data/hr_process_sequence.xml',
        'views/hr_transfer_views.xml',
        'views/hr_promotion_views.xml',
        'views/hr_disciplinary_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_process_menus.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
