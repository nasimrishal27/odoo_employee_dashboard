from odoo import models, api, fields

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def get_tiles_data(self):
        employee = self.search([('user_id', '=', self.env.uid)], limit=1)
        today = fields.Date.today()

        # Total days present
        attendance_records = self.env['hr.attendance'].search([
            ('employee_id', '=', employee.id),
        ])
        unique_days_present = set(att.check_in.date() for att in attendance_records if att.check_in)

        # Leave calculations
        leaves = self.env['hr.leave'].search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'validate'),
        ])
        total_days_taken = sum(leaves.mapped('number_of_days'))

        leaves_this_month = self.env['hr.leave'].search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'validate'),
            ('request_date_from', '<=', today.replace(day=31)),
            ('request_date_to', '>=', today.replace(day=1)),
        ])

        pending_leaves = self.env['hr.leave'].search_count([
            ('employee_id', '=', employee.id),
            ('state', 'in', ['confirm', 'validate1']),
        ])

        # 🔹 Project tasks
        tasks = self.env['project.task'].search([
            ('user_ids', '=', employee.user_id.id),
        ], limit=10)  # Optional: limit for performance

        project_tasks = [{
            'name': task.project_id.name,
            'task_name': task.name,
            'deadline': task.date_deadline.strftime('%Y-%m-%d') if task.date_deadline else '',
            'stage': task.stage_id.name,
        } for task in tasks]

        return {
            'my_attendance': employee.hours_last_month,
            'hours_today': employee.hours_today,
            'hours_previously_today': employee.hours_previously_today,
            'last_attendance_worked_hours': employee.last_attendance_worked_hours,
            'total_overtime': employee.total_overtime,
            'total_days_present': len(unique_days_present),
            'total_leaves_taken': total_days_taken,
            'leaves_this_month': sum(leaves_this_month.mapped('number_of_days')),
            'pending_leaves_count': pending_leaves,
            'project_tasks': project_tasks,
        }
