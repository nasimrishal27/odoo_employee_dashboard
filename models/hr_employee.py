from odoo import models, api, fields
from datetime import date

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def get_tiles_data(self):
        employee = self.search([('user_id', '=', self.env.uid)], limit=1)
        today = fields.Date.today()

        # Time Off records
        leaves = self.env['hr.leave'].search([
            ('employee_id', '=', employee.id),
            ('state', 'in', ['validate']),
        ])

        total_days_taken = sum(leaves.mapped('number_of_days'))

        leaves_this_month = self.env['hr.leave'].search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'validate'),
            ('request_date_from', '<=', today.replace(day=31)),  # end of month
            ('request_date_to', '>=', today.replace(day=1)),     # start of month
        ])

        pending_leaves = self.env['hr.leave'].search_count([
            ('employee_id', '=', employee.id),
            ('state', 'in', ['confirm', 'validate1']),
        ])

        return {
            'my_attendance': employee.hours_last_month,
            'hours_today': employee.hours_today,
            'hours_previously_today': employee.hours_previously_today,
            'last_attendance_worked_hours': employee.last_attendance_worked_hours,
            'attendance_state': employee.attendance_state,
            'last_check_in': employee.last_check_in,
            'last_check_out': employee.last_check_out,
            'total_overtime': employee.total_overtime,

            # 🆕 Leave Information
            'total_leaves_taken': total_days_taken,
            'leaves_this_month': sum(leaves_this_month.mapped('number_of_days')),
            'pending_leaves_count': pending_leaves,
        }
