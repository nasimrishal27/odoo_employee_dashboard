from odoo import models, fields, api
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def get_tiles_data(self, **kwargs):
        try:
            employee = self.search([('user_id', '=', self.env.uid)], limit=1)
            if not employee:
                return self._get_empty_data()

            start_date, end_date = self._compute_date_range(kwargs)
            personal_details = {
                'employee_name': employee.name,
                'employee_email': employee.work_email,
                'employee_phone': employee.work_phone,
                'employee_department': employee.department_id.name,
                'employee_job': employee.job_id.name,
                'employee_image': employee.image_1920,
            }
            return {
                **self._get_attendance_data(employee, start_date, end_date),
                **self._get_leave_data(employee, start_date, end_date),
                'project_tasks': self._get_project_tasks(employee),
                'project_task_count': self._get_project_tasks_count(employee),
                'filter_period': f"{start_date} to {end_date}",
                'personal_details': personal_details,
            }

        except Exception as e:
            _logger.error("Error in get_tiles_data: %s", e, exc_info=True)
            return self._get_empty_data()

    def _compute_date_range(self, kwargs):
        start_date = fields.Date.from_string(kwargs.get('start_date'))
        end_date = fields.Date.from_string(kwargs.get('end_date'))
        if not start_date or not end_date:
            today = fields.Date.today()
            start_date = today.replace(day=1)
            end_date = (start_date + relativedelta(months=1)) - timedelta(days=1)
        return start_date, end_date

    def _get_empty_data(self):
        return {
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
        Attendance = self.env['hr.attendance']
        domain = [
            ('employee_id', '=', employee.id),
            ('check_in', '>=', datetime.combine(start_date, datetime.min.time())),
            ('check_in', '<=', datetime.combine(end_date, datetime.max.time()))
        ]
        records = Attendance.search(domain)

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

        ongoing_attendance = Attendance.search([
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
        Leave = self.env['hr.leave']

        today = fields.Date.today()
        month_start = today.replace(day=1)
        month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)

        leaves = Leave.search([
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

        pending = Leave.search_count([
            ('employee_id', '=', employee.id),
            ('state', 'in', ['confirm', 'validate1'])
        ])

        return {
            'total_leaves_taken': total_days,
            'leaves_this_month': month_days,
            'pending_leaves_count': pending,
        }

    def _get_project_tasks(self, employee):
        if not employee.user_id:
            return []

        tasks = self.env['project.task'].search([
            ('user_ids', 'in', [employee.user_id.id]),
            ('active', '=', True)
        ], order='date_deadline asc, priority desc', limit=20)

        project = self.env['project.project'].search([
            ('user_id', 'in', [employee.user_id.id]),
            ('active', '=', True)
        ])

        return [{
            'name': task.project_id.name or 'No Project',
            'task_name': task.name,
            'deadline': task.date_deadline.strftime('%Y-%m-%d') if task.date_deadline else '',
            'stage': task.stage_id.name if task.stage_id else 'No Stage',
            'priority': task.priority or '0',
            'progress': getattr(task, 'progress', 0),
        } for task in tasks]

    def _get_project_tasks_count(self, employee):
        if not employee.user_id:
            return []

        tasks = self.env['project.task'].search([
            ('user_ids', 'in', [employee.user_id.id]),
            ('active', '=', True)
        ])

        projects = self.env['project.project'].search([
            ('user_id', 'in', [employee.user_id.id]),
            ('active', '=', True)
        ])

        return {
            'project_count': len(projects),
            'task_count': len(tasks),
            'remaining_project_count': len(projects.filtered(lambda record: record.last_update_status != 'done')),
            'remaining_task_count': len(tasks.filtered(lambda record: record.is_closed != True)),
        }

    # def _get_project_tasks(self, employee):
    #     if not employee.user_id:
    #         return {
    #             'total_projects': 0,
    #             'total_tasks': 0,
    #             'remaining_projects': 0,
    #             'remaining_tasks': 0,
    #             'tasks': [],
    #         }
    #
    #     Task = self.env['project.task']
    #     user_tasks = Task.search([
    #         ('user_ids', 'in', [employee.user_id.id]),
    #         ('active', '=', True)
    #     ])
    #
    #     # Calculate totals
    #     total_tasks = len(user_tasks)
    #     remaining_tasks = len(user_tasks.filtered(lambda t: t.stage_id and not t.stage_id.fold))
    #
    #     project_ids = user_tasks.mapped('project_id')
    #     total_projects = len(project_ids)
    #     remaining_projects = len(set(
    #         t.project_id.id for t in user_tasks
    #         if t.stage_id and not t.stage_id.fold
    #     ))
    #
    #     # Prepare task details (optional for displaying tasks)
    #     tasks_data = [{
    #         'name': task.project_id.name or 'No Project',
    #         'task_name': task.name,
    #         'deadline': task.date_deadline.strftime('%Y-%m-%d') if task.date_deadline else '',
    #         'stage': task.stage_id.name if task.stage_id else 'No Stage',
    #         'priority': task.priority or '0',
    #         'progress': getattr(task, 'progress', 0),
    #     } for task in
    #         user_tasks.sorted(key=lambda t: (t.date_deadline or fields.Date.today(), t.priority), reverse=False)[:20]]
    #
    #     return {
    #         'total_projects': total_projects,
    #         'total_tasks': total_tasks,
    #         'remaining_projects': remaining_projects,
    #         'remaining_tasks': remaining_tasks,
    #         'tasks': tasks_data,
    #     }

    # def _get_project_tasks(self, employee):
    #     if not employee.user_id:
    #         return {
    #             'total_projects': 0,
    #             'total_tasks': 0,
    #             'remaining_projects': 0,
    #             'remaining_tasks': 0,
    #             'tasks': [],
    #         }
    #
    #     Task = self.env['project.task']
    #     Project = self.env['project.project']
    #
    #     # Fetch all tasks assigned to the user
    #     user_tasks = Task.search([
    #         ('user_ids', 'in', [employee.user_id.id]),
    #         ('active', '=', True)
    #     ])
    #
    #     # Fetch all projects the user is involved in (project.user_id or message_follower_ids if needed)
    #     user_projects = Project.search([
    #         ('user_id', '=', employee.user_id.id),
    #         ('active', '=', True)
    #     ])
    #
    #     # Totals
    #     total_tasks = len(user_tasks)
    #     total_projects = len(user_projects)
    #
    #     # Remaining tasks = tasks not in folded stages
    #     remaining_tasks = len(user_tasks.filtered(lambda t: t.stage_id and not t.stage_id.fold))
    #
    #     # Remaining projects = user-assigned projects having at least one non-folded task for the user
    #     project_ids_with_remaining_tasks = set(
    #         task.project_id.id for task in user_tasks
    #         if task.project_id and task.stage_id and not task.stage_id.fold
    #     )
    #     remaining_projects = len([p for p in user_projects if p.id in project_ids_with_remaining_tasks])
    #
    #     # Task details
    #     tasks_data = [{
    #         'name': task.project_id.name or 'No Project',
    #         'task_name': task.name,
    #         'deadline': task.date_deadline.strftime('%Y-%m-%d') if task.date_deadline else '',
    #         'stage': task.stage_id.name if task.stage_id else 'No Stage',
    #         'priority': task.priority or '0',
    #         'progress': getattr(task, 'progress', 0),
    #     } for task in
    #         user_tasks.sorted(key=lambda t: (t.date_deadline or fields.Date.today(), t.priority), reverse=False)[:20]]
    #
    #     return {
    #         'total_projects': total_projects,
    #         'total_tasks': total_tasks,
    #         'remaining_projects': remaining_projects,
    #         'remaining_tasks': remaining_tasks,
    #         'tasks': tasks_data,
    #     }

