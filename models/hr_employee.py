from odoo import models, fields, api
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def get_tiles_data(self, **kwargs):
        try:
            # Find the employee linked to the current user
            employee = self.sudo().search([('user_id', '=', self.env.uid)], limit=1)
            if not employee:
                return self._get_empty_data()

            # Check if the user is a manager
            is_manager = self.env.user.has_group('hr.group_hr_manager')

            # Compute date range
            start_date, end_date, filter_date = self._compute_date_range(kwargs)

            # Base employee data
            data = {
                'is_manager': is_manager,
                'filter_period': f"{start_date} to {end_date}",
            }

            if is_manager:
                # Manager-specific data
                data.update(self._get_manager_data(filter_date))
            else:
                # Employee-specific data
                personal_details = {
                    'employee_name': employee.name,
                    'employee_email': employee.work_email,
                    'employee_phone': employee.work_phone,
                    'employee_department': employee.department_id.name,
                    'employee_job': employee.job_id.name,
                    'employee_image': employee.image_1920,
                }
                data.update({
                    **self._get_attendance_data(employee, start_date, end_date),
                    **self._get_leave_data(employee, start_date, end_date),
                    'project_tasks': self._get_project_tasks(employee),
                    'project_task_count': self._get_project_tasks_count(employee),
                    'personal_details': personal_details,
                })

            return data

        except Exception as e:
            _logger.error("Error in get_tiles_data: %s", e, exc_info=True)
            return self._get_empty_data()

    def _get_manager_data(self, filter_date):
        """Fetch manager-specific data for the current date only, attendance in days."""
        filter_date = filter_date or fields.Date.today()
        start_datetime = datetime.combine(filter_date, datetime.min.time())
        end_datetime = datetime.combine(filter_date, datetime.max.time())

        # Employees (you can filter to subordinates if needed)
        employees = self.sudo().search([])

        # Attendance data for today
        attendance = self.env['hr.attendance'].sudo().search([
            ('employee_id', 'in', employees.ids),
            ('check_in', '>=', start_datetime),
            ('check_in', '<=', end_datetime),
        ])

        # Get unique employee IDs with attendance
        present_employee_ids = set(attendance.mapped('employee_id.id'))

        # Count by gender
        men_ids = set(attendance.filtered(lambda a: a.employee_id.gender == 'male').mapped('employee_id.id'))
        women_ids = set(attendance.filtered(lambda a: a.employee_id.gender == 'female').mapped('employee_id.id'))

        total_days = len(present_employee_ids)
        men_days = len(men_ids)
        women_days = len(women_ids)

        # Leave data for today
        leaves = self.env['hr.leave'].sudo().search([
            ('employee_id', 'in', employees.ids),
            ('state', '=', 'validate'),
            ('request_date_from', '<=', filter_date),
            ('request_date_to', '>=', filter_date),
        ])
        total_leaves = sum(leave.number_of_days for leave in leaves)
        men_leaves = sum(leave.number_of_days for leave in leaves if leave.employee_id.gender == 'male')
        women_leaves = sum(leave.number_of_days for leave in leaves if leave.employee_id.gender == 'female')

        # Project data
        projects = self.env['project.project'].sudo().search([('active', '=', True)])
        tasks = self.env['project.task'].sudo().search([('active', '=', True)],
                                                       order='date_deadline asc, priority desc')
        manager_projects = [{
            'id': task.id,
            'name': task.project_id.name or 'No Project',
            'task_name': task.name,
            'deadline': task.date_deadline.strftime('%Y-%m-%d') if task.date_deadline else '',
            'stage': task.stage_id.name if task.stage_id else 'No Stage',
            'assignees': [user.name for user in task.user_ids]
        } for task in tasks]
        return {
            'manager_attendance': {
                'total': total_days,
                'men': men_days,
                'women': women_days,
            },
            'manager_leaves': {
                'total': total_leaves,
                'men': men_leaves,
                'women': women_leaves,
            },
            'manager_project_count': {
                'total_projects': len(projects),
                'total_tasks': len(tasks),
                'remaining_projects': len(projects.filtered(lambda p: p.last_update_status != 'done')),
                'remaining_tasks': len(tasks.filtered(lambda t: not t.is_closed)),
            },
            'manager_projects': manager_projects,
        }

    def _compute_date_range(self, kwargs):
        start_date = fields.Date.from_string(kwargs.get('start_date'))
        end_date = fields.Date.from_string(kwargs.get('end_date'))
        filter_date = fields.Date.from_string(kwargs.get('filter_date'))
        if not start_date or not end_date:
            today = fields.Date.today()
            start_date = today.replace(day=1)
            end_date = (start_date + relativedelta(months=1)) - timedelta(days=1)
        if not filter_date:
            filter_date = fields.Date.today()
        return start_date, end_date, filter_date

    def _get_empty_data(self):
        return {
            'is_manager': False,
            'my_attendance': 0.0,
            'hours_today': 0.0,
            'hours_previously_today': 0.0,
            'last_attendance_worked_hours': 0.0,
            'total_overtime': 0.0,
            'total_days_present': 0,
            'total_leaves_taken': 0.0,
            'leaves_this_month': 0.0,
            'pending_leaves_count': 0,
            'project_tasks': [],
        }

    def _get_attendance_data(self, employee, start_date, end_date):
        # ... (Your existing _get_attendance_data method remains unchanged)
        Attendance = self.env['hr.attendance']
        domain = [
            ('employee_id', '=', employee.id),
            ('check_in', '>=', datetime.combine(start_date, datetime.min.time())),
            ('check_in', '<=', datetime.combine(end_date, datetime.max.time()))
        ]
        records = Attendance.sudo().search(domain)

        today = fields.Date.today()
        total_hours = 0.0
        today_hours = 0.0
        unique_days = set()

        for rec in records:
            check_in = rec.check_in
            check_out = rec.check_out
            worked_hours = (check_out - check_in).total_seconds() / 3600.0 if check_out else rec.worked_hours or 0.0
            total_hours += worked_hours
            if check_in.date() == today:
                today_hours += worked_hours
            unique_days.add(check_in.date())

        ongoing_attendance = Attendance.sudo().search([
            ('employee_id', '=', employee.id),
            ('check_in', '!=', False),
            ('check_out', '=', False)
        ], limit=1, order='check_in desc')

        current_session_hours = 0.0
        if ongoing_attendance:
            current_session_hours = (fields.Datetime.now() - ongoing_attendance.check_in).total_seconds() / 3600.0

        return {
            'my_attendance': total_hours,
            'hours_today': today_hours,
            'hours_previously_today': 0.0,
            'last_attendance_worked_hours': current_session_hours,
            'total_overtime': employee.total_overtime or 0.0,
            'total_days_present': len(unique_days),
        }

    def _get_leave_data(self, employee, start_date, end_date):
        # ... (Your existing _get_leave_data method remains unchanged)
        Leave = self.env['hr.leave']
        today = fields.Date.today()
        month_start = today.replace(day=1)
        month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)

        leaves = Leave.sudo().search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'validate'),
            ('request_date_to', '>=', min(start_date, month_start)),
            ('request_date_from', '<=', max(end_date, month_end)),
        ])

        month_days = sum(
            leave.number_of_days for leave in leaves
            if leave.request_date_to >= start_date and leave.request_date_from <= end_date
        )

        total_days = sum(
            leave.number_of_days for leave in leaves
            if leave.request_date_to >= month_start and leave.request_date_from <= month_end
        )

        pending = Leave.sudo().search_count([
            ('employee_id', '=', employee.id),
            ('state', 'in', ['confirm', 'validate1'])
        ])

        return {
            'total_leaves_taken': total_days,
            'leaves_this_month': month_days,
            'pending_leaves_count': pending,
        }

    def _get_project_tasks(self, employee):
        # ... (Your existing _get_project_tasks method remains unchanged)
        if not employee.user_id:
            return []

        tasks = self.env['project.task'].sudo().search([
            ('user_ids', 'in', [employee.user_id.id]),
            ('active', '=', True)
        ], order='date_deadline asc, priority desc')

        return [{
            'id': task.id,
            'name': task.project_id.name or 'No Project',
            'task_name': task.name,
            'deadline': task.date_deadline.strftime('%Y-%m-%d') if task.date_deadline else '',
            'stage': task.stage_id.name if task.stage_id else 'No Stage',
        } for task in tasks]

    def _get_project_tasks_count(self, employee):
        # ... (Your existing _get_project_tasks_count method remains unchanged)
        if not employee.user_id:
            return []

        tasks = self.env['project.task'].sudo().search([
            ('user_ids', 'in', [employee.user_id.id]),
            ('active', '=', True)
        ])

        projects = self.env['project.project'].sudo().search([
            ('user_id', 'in', [employee.user_id.id]),
            ('active', '=', True)
        ])

        return {
            'project_count': len(projects),
            'task_count': len(tasks),
            'remaining_project_count': len(projects.filtered(lambda record: record.last_update_status != 'done')),
            'remaining_task_count': len(tasks.filtered(lambda record: record.is_closed != True)),
        }