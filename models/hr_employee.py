# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def get_tiles_data(self, **kwargs):
        try:
            employee = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.uid)], limit=1)
            if not employee:
                return self._get_empty_data()

            is_manager = self.env.user.has_group('hr.group_hr_manager')
            start_date, end_date, filter_date = self._compute_date_range(kwargs)
            data = {'is_manager': is_manager,
                    'filter_period': f"{start_date} to {end_date}",
                    'employee_hierarchy': self._get_employee_hierarchy(employee)}
            if is_manager:
                data.update(self._get_manager_data(filter_date))
            else:
                data.update({
                    **self._get_attendance_data(employee, start_date, end_date),
                    **self._get_leave_data(employee, start_date, end_date),
                    'project_tasks': self._get_project_tasks(employee),
                    'project_task_count': self._get_project_tasks_count(employee),
                    'personal_details': self._get_personal_details(employee)
                })
            return data
        except Exception:
            return self._get_empty_data()

    def _get_personal_details(self, employee):
        return {'employee_name': employee.name,
                'employee_email': employee.work_email,
                'employee_phone': employee.work_phone,
                'employee_job': employee.job_id.name,
                'employee_department': employee.department_id.name,
                'employee_image': employee.image_1920}

    def _get_employee_hierarchy(self, employee):
        hierarchy_data = []
        if employee.parent_id:
            hierarchy_data.append({'id': employee.parent_id.id,
                                   'pid': None,
                                   'name': employee.parent_id.name,
                                   'title': employee.parent_id.job_id.name or 'Manager',
                                   'img': f"/web/image/hr.employee/{employee.parent_id.id}/image_1920"})
            pid = employee.parent_id.id
        else:
            pid = None

        hierarchy_data.append({'id': employee.id,
                               'pid': pid,
                               'name': employee.name,
                               'title': employee.job_id.name or 'Employee',
                               'img': f"/web/image/hr.employee/{employee.id}/image_1920"})

        hierarchy_data.extend(self._get_subordinates(employee))
        return hierarchy_data

    def _get_subordinates(self, employee):
        def recurse(emp):
            subs = []
            for child in emp.child_ids:
                subs.append({'id': child.id,
                             'pid': emp.id,
                             'name': child.name,
                             'title': child.job_id.name or 'Employee',
                             'img': f"/web/image/hr.employee/{child.id}/image_1920"})
                subs.extend(recurse(child))
            return subs

        return recurse(employee)

    def _get_manager_data(self, filter_date):
        filter_date = filter_date or fields.Date.today()
        start_dt = datetime.combine(filter_date, datetime.min.time())
        end_dt = datetime.combine(filter_date, datetime.max.time())

        employees = self.sudo().search([])
        attendance = self.env['hr.attendance'].sudo().search([('employee_id', 'in', employees.ids),
                                                              ('check_in', '>=', start_dt),
                                                              ('check_in', '<=', end_dt)])

        def count_by_gender(gender):
            return sum(1 for a in attendance if a.employee_id.gender == gender)

        leaves = self.env['hr.leave'].sudo().search([('employee_id', 'in', employees.ids),
                                                     ('request_date_from', '<=', filter_date),
                                                     ('request_date_to', '>=', filter_date),
                                                     ('state', '=', 'validate')])

        def leave_days_by_gender(gender):
            return sum(1 for leave in leaves if leave.employee_id.gender == gender)

        tasks = self.env['project.task'].sudo().search([('active', '=', True)],
                                                       order='date_deadline asc, priority desc')
        projects = self.env['project.project'].sudo().search([('active', '=', True)])
        manager_projects = [{'id': t.id,
                             'name': t.project_id.name or 'No Project',
                             'task_name': t.name,
                             'deadline': t.date_deadline.strftime('%Y-%m-%d') if t.date_deadline else '',
                             'stage': t.stage_id.name if t.stage_id else 'No Stage',
                             'assignees': [u.name for u in t.user_ids]} for t in tasks]

        return {'manager_attendance': {'total': len(set(attendance.mapped('employee_id.id'))),
                                       'men': count_by_gender('male'),
                                       'women': count_by_gender('female')},
                'manager_leaves': {'total': sum(leave.number_of_days for leave in leaves),
                                   'men': leave_days_by_gender('male'),
                                   'women': leave_days_by_gender('female')},
                'manager_project_count': {'total_projects': len(projects),
                                          'total_tasks': len(tasks),
                                          'remaining_projects': len(projects.filtered(lambda p:
                                                                                      p.last_update_status != 'done')),
                                          'remaining_tasks': len(tasks.filtered(lambda t: not t.is_closed))},
                'manager_projects': manager_projects
                }

    def _compute_date_range(self, kwargs):
        start = fields.Date.from_string(kwargs.get('start_date')) or fields.Date.today().replace(day=1)
        end = fields.Date.from_string(kwargs.get('end_date')) or (start + relativedelta(months=1)) - timedelta(days=1)
        filter_date = fields.Date.from_string(kwargs.get('filter_date')) or fields.Date.today()
        return start, end, filter_date

    def _get_empty_data(self):
        return {'is_manager': False,
                'my_attendance': 0.0,
                'hours_today': 0.0,
                'hours_previously_today': 0.0,
                'last_attendance_worked_hours': 0.0,
                'total_overtime': 0.0,
                'total_days_present': 0,
                'total_leaves_taken': 0.0,
                'leaves_this_month': 0.0,
                'pending_leaves_count': 0,
                'project_tasks': []}

    def _get_attendance_data(self, employee, start, end):
        Attendance = self.env['hr.attendance']
        domain = [('employee_id', '=', employee.id),
                  ('check_in', '>=', datetime.combine(start, datetime.min.time())),
                  ('check_in', '<=', datetime.combine(end, datetime.max.time()))]
        records = Attendance.sudo().search(domain)
        today = fields.Date.today()
        total_hours = sum(rec.worked_hours for rec in records)
        today_hours = sum(rec.worked_hours for rec in records if rec.check_in.date() == today)
        unique_days = {rec.check_in.date() for rec in records}
        ongoing = Attendance.sudo().search([('employee_id', '=', employee.id), ('check_in', '!=', False),
                                            ('check_out', '=', False)], limit=1, order='check_in desc')
        current_session_hours = (fields.Datetime.now() - ongoing.check_in).total_seconds() / 3600 \
            if ongoing else 0.0
        return {'my_attendance': total_hours,
                'hours_today': today_hours,
                'hours_previously_today': 0.0,
                'last_attendance_worked_hours': current_session_hours,
                'total_overtime': employee.total_overtime or 0.0,
                'total_days_present': len(unique_days)}

    def _get_leave_data(self, employee, start, end):
        Leave = self.env['hr.leave']
        today = fields.Date.today()
        month_start = today.replace(day=1)
        month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)
        leaves = Leave.sudo().search([('employee_id', '=', employee.id), ('state', '=', 'validate'),
                                      ('request_date_to', '>=', min(start, month_start)),
                                      ('request_date_from', '<=', max(end, month_end))])
        total_days = sum(l.number_of_days for l in leaves if l.request_date_to >= month_start and
                         l.request_date_from <= month_end)
        month_days = sum(l.number_of_days for l in leaves if l.request_date_to >= start and
                         l.request_date_from <= end)
        pending_count = Leave.sudo().search_count([('employee_id', '=', employee.id),
                                                   ('state', 'in', ['confirm', 'validate1'])])
        return {'total_leaves_taken': total_days,
                'leaves_this_month': month_days,
                'pending_leaves_count': pending_count}

    def _get_project_tasks(self, employee):
        if not employee.user_id:
            return []
        tasks = self.env['project.task'].sudo().search([('user_ids', 'in', [employee.user_id.id]),
                                                        ('active', '=', True)],
                                                       order='date_deadline asc, priority desc')
        return [{'id': t.id,
                 'name': t.project_id.name or 'No Project',
                 'task_name': t.name,
                 'deadline': t.date_deadline.strftime('%Y-%m-%d') if t.date_deadline else '',
                 'stage': t.stage_id.name if t.stage_id else 'No Stage'} for t in tasks]

    def _get_project_tasks_count(self, employee):
        if not employee.user_id:
            return {'project_count': 0, 'task_count': 0, 'remaining_project_count': 0, 'remaining_task_count': 0}

        tasks = self.env['project.task'].sudo().search([('user_ids', 'in', [employee.user_id.id]),
                                                        ('active', '=', True)])
        projects = self.env['project.project'].sudo().search([('user_id', '=', employee.user_id.id),
                                                              ('active', '=', True)])
        return {'project_count': len(projects),
                'task_count': len(tasks),
                'remaining_project_count': len(projects.filtered(lambda p: p.last_update_status != 'done')),
                'remaining_task_count': len(tasks.filtered(lambda t: not t.is_closed))}
