# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, timedelta, time
from dateutil.relativedelta import relativedelta


class EmployeeDashboard(models.AbstractModel):
    """ Abstract Model for Employee Dashboard Data """
    _name = 'employee.dashboard'
    _description = 'Abstract Model for Employee Dashboard Data'

    @api.model
    def get_tiles_data(self, **kwargs):
        try:
            employee = self.env.user.employee_ids[:1]
            if not employee:
                return self._get_empty_data()

            is_manager = self.env.user.has_group('hr.group_hr_manager')
            start_date, end_date, filter_date = self._compute_date_range(kwargs)
            data = {
                'is_manager': is_manager,
                'filter_period': f"{start_date} to {end_date}",
                'employee_hierarchy': self._get_employee_hierarchy(employee),
                'assignees': self._get_assignees() if is_manager else [],
                'statuses': self._get_statuses(),
            }

            if is_manager:
                data.update(self._get_manager_data(filter_date, kwargs.get('assignee'), kwargs.get('deadline'), kwargs.get('status')))
            else:
                data.update({
                    **self._get_attendance_data(employee, start_date, end_date),
                    **self._get_leave_data(employee, start_date, end_date),
                    'project_tasks': self._get_project_tasks(employee, kwargs.get('deadline'), kwargs.get('status')),
                    'project_task_count': self._get_project_tasks_count(employee),
                    'personal_details': self._get_personal_details(employee)
                })
            return data
        except Exception:
            return self._get_empty_data()

    def _get_personal_details(self, employee):
        """ Function for fetching personal data """
        return {
            'employee_name': employee.name,
            'employee_email': employee.work_email,
            'employee_phone': employee.work_phone,
            'employee_job': employee.job_id.name,
            'employee_department': employee.department_id.name,
            'employee_image': employee.image_1920
        }

    def _get_assignees(self):
        """ Function for fetching assignee data for filter field """
        cr = self.env.cr
        cr.execute("""
            SELECT DISTINCT u.id, p.name
            FROM res_users u
            JOIN res_partner p ON u.partner_id = p.id
            JOIN project_task_user_rel rel ON u.id = rel.user_id
            WHERE u.active = TRUE
            ORDER BY p.name
        """)
        return [{'id': row[0], 'name': row[1]} for row in cr.fetchall()]

    def _get_statuses(self):
        """ Function for fetching status data for filter field """
        cr = self.env.cr
        lang = self.env.lang or 'en_US'
        cr.execute("""
            SELECT DISTINCT ON (name) id, name
            FROM project_task_type
            WHERE active = TRUE
            ORDER BY name, id
        """)
        return [{
            'id': row[0],
            'name': row[1].get(lang) if isinstance(row[1], dict) else row[1]
        } for row in cr.fetchall()]

    def _get_employee_hierarchy(self, employee):
        """ Function for fetching employee hierarchy data """
        cr = self.env.cr
        lang = self.env.lang or 'en_US'

        query = """WITH RECURSIVE emp_tree AS (
                    SELECT e.id, e.parent_id, e.name, e.job_id 
                    FROM hr_employee e WHERE e.id = %s
                    UNION ALL
                    SELECT e.id, e.parent_id, e.name, e.job_id 
                    FROM hr_employee e
                    INNER JOIN emp_tree et ON e.parent_id = et.id)
                SELECT et.id, et.parent_id, et.name, j.name AS job_name 
                FROM emp_tree et
                LEFT JOIN hr_job j ON et.job_id = j.id
                UNION
                SELECT m.id, m.parent_id, m.name, j.name AS job_name 
                FROM hr_employee m
                LEFT JOIN hr_job j ON m.job_id = j.id 
                WHERE m.id = (SELECT parent_id FROM hr_employee WHERE id = %s)"""

        cr.execute(query, (employee.id, employee.id))
        rows = cr.fetchall()
        hierarchy_data = []
        for emp_id, parent_id, name, job_name in rows:
            hierarchy_data.append({
                'id': emp_id,
                'pid': parent_id,
                'name': name,
                'title': job_name.get(lang) if isinstance(job_name, dict) else job_name,
                'img': f"/web/image/hr.employee/{emp_id}/image_1920"
            })
        return hierarchy_data

    def _get_manager_data(self, filter_date, assignee, deadline, status):
        """ Function for fetching manager wise data """
        filter_date = filter_date or fields.Date.today()
        start_dt = datetime.combine(filter_date, datetime.min.time())
        end_dt = datetime.combine(filter_date, datetime.max.time())

        cr = self.env.cr
        lang = self.env.lang or 'en_US'

        # Attendance Counts
        cr.execute("""
            SELECT DISTINCT a.employee_id 
            FROM hr_attendance a
            JOIN hr_employee e ON a.employee_id = e.id
            WHERE a.check_in >= %s 
                AND a.check_in <= %s
        """, (start_dt, end_dt))
        total_attendance = len(cr.fetchall())

        cr.execute("""
            SELECT e.gender, COUNT(DISTINCT a.employee_id) 
            FROM hr_attendance a
            JOIN hr_employee e ON a.employee_id = e.id
            WHERE a.check_in >= %s 
                AND a.check_in <= %s
            GROUP BY e.gender
        """, (start_dt, end_dt))
        gender_counts = dict(cr.fetchall())

        men_attendance = gender_counts.get('male', 0)
        women_attendance = gender_counts.get('female', 0)

        # Leave Counts
        cr.execute("""
            SELECT SUM(l.number_of_days), e.gender 
            FROM hr_leave l
            JOIN hr_employee e ON l.employee_id = e.id
            WHERE l.request_date_from <= %s 
                AND l.request_date_to >= %s 
                AND l.state = %s
            GROUP BY e.gender
        """, (filter_date, filter_date, 'validate'))
        leave_data = dict((row[1], row[0] or 0) for row in cr.fetchall())

        total_leaves = sum(leave_data.values())
        men_leaves = leave_data.get('male', 0)
        women_leaves = leave_data.get('female', 0)

        # Project & Task Counts
        cr.execute("SELECT COUNT(*) FROM project_project WHERE active = %s", (True,))
        total_projects = cr.fetchone()[0]

        cr.execute("SELECT COUNT(*) FROM project_task WHERE active = %s", (True,))
        total_tasks = cr.fetchone()[0]

        cr.execute("""
            SELECT COUNT(*) 
            FROM project_project
            WHERE active = %s 
                AND last_update_status != %s
        """, (True, 'done'))
        remaining_projects = cr.fetchone()[0]

        cr.execute("""
            SELECT COUNT(*) 
            FROM project_task_user_rel rel
            JOIN project_task t ON rel.task_id = t.id
            JOIN project_task_type stage ON t.stage_id = stage.id
            WHERE t.active = TRUE 
                AND (stage.fold = FALSE OR stage.fold IS NULL)
        """)
        remaining_tasks = cr.fetchone()[0]

        query = """
            SELECT t.id, p.name, t.name, t.date_deadline, stage.name,
                ARRAY_AGG(partner.name ORDER BY partner.name)
            FROM project_task t
            LEFT JOIN project_project p ON t.project_id = p.id
            LEFT JOIN project_task_type stage ON t.stage_id = stage.id
            LEFT JOIN project_task_user_rel rel ON t.id = rel.task_id
            LEFT JOIN res_users u ON rel.user_id = u.id
            LEFT JOIN res_partner partner ON u.partner_id = partner.id
            WHERE t.active = TRUE
        """
        params = []
        if assignee:
            query += " AND u.id = %s"
            params.append(int(assignee))
        if deadline:
            query += " AND DATE(t.date_deadline) >= %s"
            params.append(deadline)
        if status:
            query += " AND t.stage_id = %s"
            params.append(int(status))
        query += """
            GROUP BY t.id, p.name, t.name, t.date_deadline, stage.name
            ORDER BY t.date_deadline ASC NULLS LAST, t.priority DESC NULLS LAST
        """
        cr.execute(query, params)
        manager_projects = []
        for t_id, project_name, task_name, date_deadline, stage_name, assignees in cr.fetchall():
            manager_projects.append({
                'id': t_id,
                'name': project_name.get(lang) if isinstance(project_name, dict) else project_name or 'No Project',
                'task_name': task_name,
                'deadline': date_deadline.strftime('%Y-%m-%d') if date_deadline else '',
                'stage': stage_name.get(lang) if isinstance(stage_name, dict) else stage_name or 'No Stage',
                'assignees': assignees
            })

        return {
            'manager_attendance': {
                'total': total_attendance,
                'men': men_attendance,
                'women': women_attendance
            },
            'manager_leaves': {
                'total': total_leaves,
                'men': men_leaves,
                'women': women_leaves
            },
            'manager_project_count': {
                'total_projects': total_projects,
                'total_tasks': total_tasks,
                'remaining_projects': remaining_projects,
                'remaining_tasks': remaining_tasks
            },
            'manager_projects': manager_projects,
            'filter_start_date': start_dt,
            'filter_end_date': end_dt,
        }

    def _compute_date_range(self, kwargs):
        """ Function for compute date range """
        start = fields.Date.from_string(kwargs.get('start_date')) or fields.Date.today().replace(day=1)
        end = fields.Date.from_string(kwargs.get('end_date')) or (start + relativedelta(months=1)) - timedelta(days=1)
        filter_date = fields.Date.from_string(kwargs.get('filter_date')) or fields.Date.today()
        return start, end, filter_date

    def _get_empty_data(self):
        """ Function for setting empty data """
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
            'assignees': [],
            'statuses': [],
        }

    def _get_attendance_data(self, employee, start, end):
        """ Function for fetching employee's attendance data """
        cr = self.env.cr
        start_datetime = datetime.combine(start, time.min).strftime('%Y-%m-%d %H:%M:%S')
        end_datetime = datetime.combine(end, time.max).strftime('%Y-%m-%d %H:%M:%S')
        today = fields.Date.today().strftime('%Y-%m-%d')

        cr.execute("""
            SELECT check_in, check_out, worked_hours, DATE(check_in AT TIME ZONE 'UTC') as check_in_date
            FROM hr_attendance
            WHERE employee_id = %s 
                AND check_in >= %s 
                AND check_in <= %s
            ORDER BY check_in
        """, (employee.id, start_datetime, end_datetime))
        records = cr.dictfetchall()

        total_hours = sum(rec['worked_hours'] or 0 for rec in records)
        today_hours = sum(rec['worked_hours'] or 0 for rec in records if rec['check_in_date'].strftime('%Y-%m-%d') == today)
        unique_days = {rec['check_in_date'] for rec in records}

        cr.execute("""
            SELECT check_in 
            FROM hr_attendance
            WHERE employee_id = %s 
                AND check_in IS NOT NULL 
                AND check_out IS NULL
            ORDER BY check_in DESC LIMIT 1
        """, (employee.id,))
        ongoing = cr.fetchone()

        current_session_hours = 0.0
        if ongoing:
            check_in_time = ongoing[0]
            current_session_hours = (fields.Datetime.now() - check_in_time).total_seconds() / 3600

        return {
            'my_attendance': total_hours,
            'hours_today': today_hours,
            'hours_previously_today': 0.0,
            'last_attendance_worked_hours': current_session_hours,
            'total_overtime': employee.total_overtime or 0.0,
            'total_days_present': len(unique_days)
        }

    def _get_leave_data(self, employee, start, end):
        """ Function for fetching employee's leave data """
        cr = self.env.cr
        today = fields.Date.context_today(self)
        month_start = today.replace(day=1)
        month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)

        cr.execute("""
            SELECT COALESCE(SUM(number_of_days), 0) 
            FROM hr_leave
            WHERE employee_id = %s  
                AND state = 'validate' 
                AND request_date_to >= %s 
                AND request_date_from <= %s
        """, (employee.id, month_start, month_end))
        total_days = cr.fetchone()[0]

        cr.execute("""
            SELECT COALESCE(SUM(number_of_days), 0) 
            FROM hr_leave
            WHERE employee_id = %s 
                AND state = 'validate' 
                AND request_date_to >= %s 
                AND request_date_from <= %s
        """, (employee.id, start, end))
        month_days = cr.fetchone()[0]

        cr.execute("""
            SELECT COUNT(*) 
            FROM hr_leave
            WHERE employee_id = %s 
                AND state IN ('confirm', 'validate1')
        """, (employee.id,))
        pending_count = cr.fetchone()[0]

        return {
            'total_leaves_taken': total_days,
            'leaves_this_month': month_days,
            'pending_leaves_count': pending_count
        }

    def _get_project_tasks(self, employee, deadline, status):
        """ Function for fetching employee's project & task data """
        if not employee.user_id:
            return []

        user_id = employee.user_id.id
        cr = self.env.cr
        lang = self.env.lang

        query = """
            SELECT t.id, p.name, t.name, t.date_deadline, stage.name
            FROM project_task_user_rel rel
            JOIN project_task t ON rel.task_id = t.id
            LEFT JOIN project_project p ON t.project_id = p.id
            LEFT JOIN project_task_type stage ON t.stage_id = stage.id
            WHERE rel.user_id = %s 
                AND t.active = TRUE
        """
        params = [user_id]
        if deadline:
            query += " AND DATE(t.date_deadline) >= %s"
            params.append(deadline)
        if status:
            query += " AND t.stage_id = %s"
            params.append(int(status))
        query += """
            ORDER BY t.date_deadline ASC NULLS LAST, t.priority DESC NULLS LAST
        """
        cr.execute(query, params)

        tasks = []
        for t_id, project_name, task_name, date_deadline, stage_name in cr.fetchall():
            tasks.append({
                'id': t_id,
                'name': project_name.get(lang) if isinstance(project_name, dict) else project_name or 'No Project',
                'task_name': task_name,
                'deadline': date_deadline.strftime('%Y-%m-%d') if date_deadline else '',
                'stage': stage_name.get(lang) if isinstance(stage_name, dict) else stage_name or 'No Stage',
            })
        return tasks

    def _get_project_tasks_count(self, employee):
        """ Function for fetching employee's project & task data count """
        if not employee.user_id:
            return {
                'project_count': 0,
                'task_count': 0,
                'remaining_project_count': 0,
                'remaining_task_count': 0
            }

        user_id = employee.user_id.id
        cr = self.env.cr

        cr.execute("""
            SELECT COUNT(*)
            FROM project_task_user_rel rel
            JOIN project_task t ON rel.task_id = t.id
            WHERE rel.user_id = %s
              AND t.active = TRUE
        """, (user_id,))
        task_count = cr.fetchone()[0]

        cr.execute("""
            SELECT COUNT(*)
            FROM project_task_user_rel rel
            JOIN project_task t ON rel.task_id = t.id
            JOIN project_task_type stage ON t.stage_id = stage.id
            WHERE rel.user_id = %s
              AND t.active = TRUE
              AND (stage.fold = FALSE OR stage.fold IS NULL)
        """, (user_id,))
        remaining_task_count = cr.fetchone()[0]

        cr.execute("""
            SELECT COUNT(*)
            FROM project_project
            WHERE user_id = %s
              AND active = TRUE
        """, (user_id,))
        project_count = cr.fetchone()[0]

        cr.execute("""
            SELECT COUNT(*)
            FROM project_project
            WHERE user_id = %s
              AND active = TRUE
              AND (last_update_status != 'done' OR last_update_status IS NULL)
        """, (user_id,))
        remaining_project_count = cr.fetchone()[0]

        return {
            'project_count': project_count,
            'task_count': task_count,
            'remaining_project_count': remaining_project_count,
            'remaining_task_count': remaining_task_count
        }
