/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";

class EmployeeDashboard extends Component {
    setup() {
        super.setup();
        this.orm = useService('orm');
        this._fetch_data();
    }

    async _fetch_data() {
        const result = await this.orm.call("hr.employee", "get_tiles_data", [], {});

        // Attendance Info HTML
        document.getElementById('my_attendance').innerHTML = `
            <div><strong>This Month:</strong> ${result.my_attendance.toFixed(2)} hrs</div>
            <div><strong>Today:</strong> ${result.hours_today.toFixed(2)} hrs</div>
            <div><strong>Ongoing:</strong> ${result.last_attendance_worked_hours.toFixed(2)} hrs</div>
            <div><strong>Overtime:</strong> ${result.total_overtime.toFixed(2)} hrs</div>
            <div><strong>Total Days:</strong> ${result.total_days_present} Days</div>
        `;

        // Leave Info HTML
        document.getElementById('my_leaves').innerHTML = `
            <div><strong>Total Leaves Taken:</strong> ${result.total_leaves_taken.toFixed(1)} days</div>
            <div><strong>Leaves This Month:</strong> ${result.leaves_this_month.toFixed(1)} days</div>
            <div><strong>Pending Leave Requests:</strong> ${result.pending_leaves_count}</div>
        `;

        new Chart(document.getElementById("attendanceChart"), {
            type: 'doughnut',
            data: {
                labels: ['Month Total', 'Today', 'Ongoing', 'Overtime'],
                datasets: [{
                    label: 'Hours',
                    data: [
                        result.my_attendance,
                        result.hours_today,
                        result.last_attendance_worked_hours,
                        result.total_overtime
                    ],
                    backgroundColor: ['#36A2EB', '#4BC0C0', '#FFCE56', '#FF6384'],
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Attendance Summary'
                    }
                }
            }
        });

        new Chart(document.getElementById("leaveChart"), {
            type: 'bar',
            data: {
                labels: ['Total Taken', 'This Month', 'Pending'],
                datasets: [{
                    label: 'Leave (days)',
                    data: [
                        result.total_leaves_taken,
                        result.leaves_this_month,
                        result.pending_leaves_count
                    ],
                    backgroundColor: ['#36A2EB', '#FF6384', '#FFCE56'],
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Leave Summary'
                    }
                },
            }
        });

        // 🆕 Populate Projects Table
    const projectBody = document.getElementById("projectTableBody");
    projectBody.innerHTML = ""; // Clear previous

    result.project_tasks.forEach(task => {
        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${task.name || '-'}</td>
            <td>${task.task_name || '-'}</td>
            <td>${task.deadline || '-'}</td>
            <td>${task.stage || '-'}</td>
        `;
        projectBody.appendChild(row);
    });
    }
}

EmployeeDashboard.template = "employee_dashboard.EmployeeDashboard";
registry.category("actions").add("employee_dashboard_tag", EmployeeDashboard);
