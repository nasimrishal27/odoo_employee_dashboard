/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onMounted } from "@odoo/owl";

class EmployeeDashboard extends Component {
    setup() {
        super.setup();
        this.orm = useService('orm');
        this.state = useState({
            data: null,
            loading: true,
            filters: {
                type: 'months',
                value: 'current',
                startDate: null,
                endDate: null
            }
        });

        onMounted(() => {
            this._initializeDates();
            this._fetch_data();
        });
    }

    _initializeDates() {
        const today = new Date();
        const firstDayOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
        const lastDayOfMonth = new Date(today.getFullYear(), today.getMonth() + 1, 0);

        this.state.filters.startDate = firstDayOfMonth.toISOString().split('T')[0];
        this.state.filters.endDate = lastDayOfMonth.toISOString().split('T')[0];

        setTimeout(() => {
            const startDateEl = document.getElementById('startDate');
            const endDateEl = document.getElementById('endDate');
            if (startDateEl) startDateEl.value = this.state.filters.startDate;
            if (endDateEl) endDateEl.value = this.state.filters.endDate;
        }, 100);
    }

    _getFilterLabel() {
        const { type, value } = this.state.filters;
        const map = {
            days: {
                today: "Today",
                yesterday: "Yesterday",
                last7: "Last 7 Days",
                last15: "Last 15 Days",
                last30: "Last 30 Days",
            },
            months: {
                current: "This Month",
                last: "Last Month",
                last3: "Last 3 Months",
                last6: "Last 6 Months",
                last12: "Last 12 Months",
            },
            years: {
                current: "This Year",
                last: "Last Year",
            }
        };
        if (type === 'years' && !isNaN(parseInt(value))) {
            return value;
        }
        return map[type]?.[value] || "Custom Range";
    }

    async _fetch_data() {
        try {
            this.state.loading = true;
            const result = await this.orm.call("hr.employee", "get_tiles_data", [], {
                filter_type: this.state.filters.type,
                filter_value: this.state.filters.value,
                start_date: this.state.filters.startDate,
                end_date: this.state.filters.endDate
            });
            this.state.data = result;
            this.state.loading = false;

            await new Promise(resolve => setTimeout(resolve, 100));
            this._updateContent();
            this._createCharts();
        } catch (error) {
            console.error("Error fetching dashboard data:", error);
            this.state.loading = false;
        }
    }

    onFilterTypeChange(event) {
        this.state.filters.type = event.target.value;
        this._updateFilterOptions();
    }

    onDateFilterChange(event) {
        this.state.filters.value = event.target.value;
        this._updateDateRange();
    }

    onCustomDateChange() {
        const startDateEl = document.getElementById('startDate');
        const endDateEl = document.getElementById('endDate');
        if (startDateEl && endDateEl) {
            this.state.filters.startDate = startDateEl.value;
            this.state.filters.endDate = endDateEl.value;
        }
    }

    _updateFilterOptions() {
        const filterEl = document.getElementById('dateFilter');
        if (!filterEl) return;

        let options = '';
        const filterType = this.state.filters.type;
        const currentYear = new Date().getFullYear();

        if (filterType === 'days') {
            options = `
                <option value="today">Today</option>
                <option value="yesterday">Yesterday</option>
                <option value="last7">Last 7 Days</option>
                <option value="last15">Last 15 Days</option>
                <option value="last30">Last 30 Days</option>
            `;
        } else if (filterType === 'months') {
            options = `
                <option value="current">Current Month</option>
                <option value="last">Last Month</option>
                <option value="last3">Last 3 Months</option>
                <option value="last6">Last 6 Months</option>
                <option value="last12">Last 12 Months</option>
            `;
        } else if (filterType === 'years') {
            options = `
                <option value="current">Current Year</option>
                <option value="last">Last Year</option>
                <option value="${currentYear}">${currentYear}</option>
                <option value="${currentYear - 1}">${currentYear - 1}</option>
                <option value="${currentYear - 2}">${currentYear - 2}</option>
            `;
        }

        filterEl.innerHTML = options;
        this.state.filters.value = filterEl.value;
        this._updateDateRange();
    }

    _updateDateRange() {
        const today = new Date();
        let startDate, endDate;
        const { type, value } = this.state.filters;

        if (type === 'days') {
            switch (value) {
                case 'today':
                    startDate = endDate = new Date(today);
                    break;
                case 'yesterday':
                    startDate = endDate = new Date(today.getTime() - 24 * 60 * 60 * 1000);
                    break;
                case 'last7':
                    startDate = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
                    endDate = new Date(today);
                    break;
                case 'last15':
                    startDate = new Date(today.getTime() - 15 * 24 * 60 * 60 * 1000);
                    endDate = new Date(today);
                    break;
                case 'last30':
                    startDate = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);
                    endDate = new Date(today);
                    break;
            }
        } else if (type === 'months') {
            switch (value) {
                case 'current':
                    startDate = new Date(today.getFullYear(), today.getMonth(), 1);
                    endDate = new Date(today.getFullYear(), today.getMonth() + 1, 0);
                    break;
                case 'last':
                    startDate = new Date(today.getFullYear(), today.getMonth() - 1, 1);
                    endDate = new Date(today.getFullYear(), today.getMonth(), 0);
                    break;
                case 'last3':
                    startDate = new Date(today.getFullYear(), today.getMonth() - 3, 1);
                    endDate = new Date(today);
                    break;
                case 'last6':
                    startDate = new Date(today.getFullYear(), today.getMonth() - 6, 1);
                    endDate = new Date(today);
                    break;
                case 'last12':
                    startDate = new Date(today.getFullYear(), today.getMonth() - 12, 1);
                    endDate = new Date(today);
                    break;
            }
        } else if (type === 'years') {
            if (value === 'current') {
                startDate = new Date(today.getFullYear(), 0, 1);
                endDate = new Date(today.getFullYear(), 11, 31);
            } else if (value === 'last') {
                startDate = new Date(today.getFullYear() - 1, 0, 1);
                endDate = new Date(today.getFullYear() - 1, 11, 31);
            } else {
                const year = parseInt(value);
                startDate = new Date(year, 0, 1);
                endDate = new Date(year, 11, 31);
            }
        }

        if (startDate && endDate) {
            this.state.filters.startDate = startDate.toISOString().split('T')[0];
            this.state.filters.endDate = endDate.toISOString().split('T')[0];

            const startDateEl = document.getElementById('startDate');
            const endDateEl = document.getElementById('endDate');
            if (startDateEl) startDateEl.value = this.state.filters.startDate;
            if (endDateEl) endDateEl.value = this.state.filters.endDate;
        }
    }

    async applyFilter() {
        await this._fetch_data();
    }

    _updateContent() {
        if (!this.state.data) return;
        const result = this.state.data;
        const filterLabel = this._getFilterLabel();

        const attendanceEl = document.getElementById('my_attendance');
        if (attendanceEl) {
            attendanceEl.innerHTML = `
                <table>
                <tr><td><strong>${filterLabel}:</strong></td> <td>${result.my_attendance.toFixed(2)} hrs</td></tr>
                <tr><td><strong>Today:</strong></td> <td> ${result.hours_today.toFixed(2)} hrs</td></tr>
                <tr><td><strong>Ongoing:</strong></td> <td> ${result.last_attendance_worked_hours.toFixed(2)} hrs</td></tr>
                <tr><td><strong>Overtime:</strong></td> <td> ${result.total_overtime.toFixed(2)} hrs</td></tr>
                <tr><td><strong>Total Days:</strong></td> <td> ${result.total_days_present} Days</td></tr>
                </table>
            `;
            document.getElementById('employeeImage').innerHTML = `
                <img src="data:image/png;base64,${result.personal_details.employee_image}" width="100%" height="100%"/>
            `;
        }

        const informationEl = document.getElementById('my_information');
        if (informationEl) {
            informationEl.innerHTML = `
                <table>
                <tr><td><strong>Name:</strong></td> <td> ${result.personal_details.employee_name}</td></tr>
                <tr><td><strong>Email:</strong></td> <td> ${result.personal_details.employee_email}</td></tr>
                <tr><td><strong>Phone:</strong></td> <td> ${result.personal_details.employee_phone}</td></tr>
                <tr><td><strong>Department:</strong></td> <td> ${result.personal_details.employee_department}</td></tr>
                <tr><td><strong>Job:</strong></td> <td> ${result.personal_details.employee_job}</td></tr>
                </table>
            `;
        }

        const leavesEl = document.getElementById('my_leaves');
        if (leavesEl) {
            leavesEl.innerHTML = `
                <table>
                <tr><td><strong>Total Leaves Taken:</strong></td> <td> ${result.total_leaves_taken.toFixed(1)} days</td></tr>
                <tr><td><strong>${filterLabel}:</strong></td> <td> ${result.leaves_this_month.toFixed(1)} days</td></tr>
                <tr><td><strong>Pending Leave Requests:</strong></td> <td> ${result.pending_leaves_count}</td></tr>
                </table>
            `;
        }

        const projectBody = document.getElementById("taskTableBody");
        if (projectBody) {
            projectBody.innerHTML = "";
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

        document.getElementById('projectCount').textContent = result.project_task_count.project_count;
        document.getElementById('taskCount').textContent = result.project_task_count.task_count;
        document.getElementById('remainingProjectCount').textContent = result.project_task_count.remaining_project_count;
        document.getElementById('remainingTaskCount').textContent = result.project_task_count.remaining_task_count;

    }

    _createCharts() {
        if (!this.state.data) return;
        const result = this.state.data;
        const filterLabel = this._getFilterLabel();

        const attendanceCanvas = document.getElementById("attendanceChart");
        if (attendanceCanvas) {
            new Chart(attendanceCanvas, {
                type: 'doughnut',
                data: {
                    labels: [filterLabel, 'Today', 'Ongoing', 'Overtime'],
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
                    maintainAspectRatio: true,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Attendance Summary'
                        }
                    }
                }
            });
        }

        const leaveCanvas = document.getElementById("leaveChart");
        if (leaveCanvas) {
            new Chart(leaveCanvas, {
                type: 'bar',
                data: {
                    labels: ['Total Taken', filterLabel, 'Pending'],
                    datasets: [{
                        label: ['Leave (days)'],
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
                    maintainAspectRatio: true,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Leave Summary'
                        }
                    }
                }
            });
        }
    }

    async refreshData() {
        await this._fetch_data();
    }
}

EmployeeDashboard.template = "employee_dashboard.EmployeeDashboard";
registry.category("actions").add("employee_dashboard_tag", EmployeeDashboard);
