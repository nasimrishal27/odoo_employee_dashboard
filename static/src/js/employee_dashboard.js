/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onMounted } from "@odoo/owl";

class Dashboard extends Component {
    static template = "employee_dashboard.EmployeeDashboard";

    setup() {
        super.setup();
        this.orm = useService('orm');
        this.action = useService("action");
        this.chartInstances = {};
        this.state = useState({
            data: null,
            loading: true,
            filters: {
                type: 'months',
                value: 'current',
                startDate: null,
                endDate: null,
                filterDate: null,
                assignee: '',
                deadline: null,
                status: '',
            },
            assignees: [],
            statuses: [],
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
            const filterDateEl = document.getElementById('filterDate');
            if (startDateEl) startDateEl.value = this.state.filters.startDate;
            if (endDateEl) endDateEl.value = this.state.filters.endDate;
            if (filterDateEl) filterDateEl.value = this.state.filters.filterDate;
            this._populateAssigneeOptions();
            this._populateStatusOptions();
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
            const result = await this.orm.call("employee.dashboard", "get_tiles_data", [], {
                filter_type: this.state.filters.type,
                filter_value: this.state.filters.value,
                start_date: this.state.filters.startDate,
                end_date: this.state.filters.endDate,
                filter_date: this.state.filters.filterDate,
                assignee: this.state.is_manager ? this.state.filters.assignee : null,
                deadline: this.state.filters.deadline,
                status: this.state.filters.status,
            });
            this.state.data = result;
            this.state.loading = false;
            this.state.is_manager = result.is_manager;
            this.state.assignees = result.assignees || [];
            this.state.statuses = result.statuses || [];

            await new Promise(resolve => setTimeout(resolve, 100));
            this._updateContent();
            this._createCharts();
            if (this.state.is_manager) {
                this._populateAssigneeOptions();
            }
            this._populateStatusOptions();
            // Update filter inputs for Employee Dashboard
            if (!this.state.is_manager) {
                const deadlineEl = document.getElementById('deadlineFilter');
                const statusEl = document.getElementById('statusFilter');
                if (deadlineEl) deadlineEl.value = this.state.filters.deadline || '';
                if (statusEl) statusEl.value = this.state.filters.status || '';
            }
        } catch (error) {
            console.error("Error fetching dashboard data:", error);
            this.state.loading = false;
        }
    }

    _populateAssigneeOptions() {
        const assigneeEl = document.getElementById('managerAssigneeFilter');
        if (!assigneeEl) return;
        let options = '<option value="">All Assignees</option>';
        this.state.assignees.forEach(assignee => {
            options += `<option value="${assignee.id}">${assignee.name}</option>`;
        });
        assigneeEl.innerHTML = options;
        assigneeEl.value = this.state.filters.assignee || '';
    }

    _populateStatusOptions() {
        const statusEl = document.getElementById(this.state.is_manager ? 'managerStatusFilter' : 'statusFilter');
        if (!statusEl) return;
        let options = '<option value="">All Statuses</option>';
        this.state.statuses.forEach(status => {
            options += `<option value="${status.id}">${status.name}</option>`;
        });
        statusEl.innerHTML = options;
        statusEl.value = this.state.filters.status || '';
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
        const filterDateEl = document.getElementById('filterDate');
        if (startDateEl && endDateEl) {
            this.state.filters.startDate = startDateEl.value;
            this.state.filters.endDate = endDateEl.value;
        }
        if (filterDateEl) {
            this.state.filters.filterDate = filterDateEl.value;
        }
    }

    onAssigneeFilterChange(event) {
        this.state.filters.assignee = event.target.value;
    }

    onDeadlineFilterChange(event) {
        this.state.filters.deadline = event.target.value || null;
    }

    onStatusFilterChange(event) {
        this.state.filters.status = event.target.value;
    }

    async applyTaskFilter() {
        await this._fetch_data();
    }

    async clearTaskFilter() {
        this.state.filters.assignee = '';
        this.state.filters.deadline = null;
        this.state.filters.status = '';
        const assigneeEl = document.getElementById('managerAssigneeFilter');
        const deadlineEl = document.getElementById(this.state.is_manager ? 'managerDeadlineFilter' : 'deadlineFilter');
        const statusEl = document.getElementById(this.state.is_manager ? 'managerStatusFilter' : 'statusFilter');
        if (assigneeEl) assigneeEl.value = '';
        if (deadlineEl) deadlineEl.value = '';
        if (statusEl) statusEl.value = '';
        await this._fetch_data();
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
        if (this.state.data.is_manager) {
            const result = this.state.data;
            document.getElementById('manager_attendance_total').textContent = result.manager_attendance.total;
            document.getElementById('manager_attendance_men').textContent = result.manager_attendance.men;
            document.getElementById('manager_attendance_women').textContent = result.manager_attendance.women;
            document.getElementById('manager_leave_total').textContent = result.manager_leaves.total;
            document.getElementById('manager_leave_men').textContent = result.manager_leaves.men;
            document.getElementById('manager_leave_women').textContent = result.manager_leaves.women;
            document.getElementById('manager_total_projects').textContent = result.manager_project_count.total_projects;
            document.getElementById('manager_total_tasks').textContent = result.manager_project_count.total_tasks;
            document.getElementById('manager_remaining_projects').textContent = result.manager_project_count.remaining_projects;
            document.getElementById('manager_remaining_tasks').textContent = result.manager_project_count.remaining_tasks;
            const projectBody = document.getElementById("managerTaskTableBody");
            if (projectBody) {
                projectBody.innerHTML = "";
                result.manager_projects.forEach(task => {
                    const row = document.createElement("tr");
                    row.onclick = () => {
                        this.action.doAction({
                            type: 'ir.actions.act_window',
                            name: 'Task',
                            res_model: 'project.task',
                            res_id: task.id,
                            views: [
                                [false, "form"],
                            ],
                        });
                    };
                    row.innerHTML = `
                        <td>${task.task_name || '-'}</td>
                        <td>${task.name || '-'}</td>
                        <td>${task.deadline || '-'}</td>
                        <td>${task.stage || '-'}</td>
                        <td>${task.assignees ? task.assignees.join(', ') : '-'}</td>
                    `;
                    projectBody.appendChild(row);
                });
            }
        } else {
            const result = this.state.data;
            const filterLabel = this._getFilterLabel();
            const attendanceEl = document.getElementById('my_attendance');
            if (attendanceEl) {
                attendanceEl.innerHTML = `
                    <table>
                    <tr><td><strong>${filterLabel}:</strong></td>
                    <td class="ps-5">${result.my_attendance.toFixed(2)} hrs</td></tr>
                    <tr><td><strong>Today:</strong></td>
                    <td class="ps-5"> ${result.hours_today.toFixed(2)} hrs</td></tr>
                    <tr><td><strong>Ongoing:</strong></td>
                    <td class="ps-5"> ${result.last_attendance_worked_hours.toFixed(2)} hrs</td></tr>
                    <tr><td><strong>Overtime:</strong></td>
                    <td class="ps-5"> ${result.total_overtime.toFixed(2)} hrs</td></tr>
                    <tr><td><strong>Total Days:</strong></td>
                    <td class="ps-5"> ${result.total_days_present} Days</td></tr>
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
                    <tr><td><strong>Name:</strong></td>
                    <td class="ps-3"> ${result.personal_details.employee_name}</td></tr>
                    <tr><td><strong>Email:</strong></td>
                    <td class="ps-3"> ${result.personal_details.employee_email}</td></tr>
                    <tr><td><strong>Phone:</strong></td>
                    <td class="ps-3"> ${result.personal_details.employee_phone}</td></tr>
                    <tr><td><strong>Department:</strong></td>
                    <td class="ps-3"> ${result.personal_details.employee_department}</td></tr>
                    <tr><td><strong>Job:</strong></td>
                    <td class="ps-3"> ${result.personal_details.employee_job}</td></tr>
                    </table>
                `;
            }
            const leavesEl = document.getElementById('my_leaves');
            if (leavesEl) {
                leavesEl.innerHTML = `
                    <table>
                    <tr><td><strong>Total Leaves Taken:</strong></td>
                    <td class="ps-5"> ${result.total_leaves_taken.toFixed(1)} days</td></tr>
                    <tr><td><strong>${filterLabel}:</strong></td>
                    <td class="ps-5"> ${result.leaves_this_month.toFixed(1)} days</td></tr>
                    <tr><td><strong>Pending Leave Requests:</strong></td>
                    <td class="ps-5"> ${result.pending_leaves_count}</td></tr>
                    </table>
                `;
            }
            const projectBody = document.getElementById("taskTableBody");
            if (projectBody) {
                projectBody.innerHTML = "";
                result.project_tasks.forEach(task => {
                    const row = document.createElement("tr");
                    row.onclick = () => {
                        this.action.doAction({
                            type: 'ir.actions.act_window',
                            name: 'Task',
                            res_model: 'project.task',
                            res_id: task.id,
                            views: [
                                [false, "form"],
                            ],
                        });
                    };
                    row.innerHTML = `
                        <td>${task.task_name || '-'}</td>
                        <td>${task.name || '-'}</td>
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
    }

    _destroyExistingCharts() {
        Object.keys(this.chartInstances).forEach(chartId => {
            if (this.chartInstances[chartId]) {
                this.chartInstances[chartId].destroy();
                delete this.chartInstances[chartId];
            }
        });
    }

    _createCharts() {
        const result = this.state.data;
        if (!result) return;
        this._destroyExistingCharts();
        if (result.employee_hierarchy && result.employee_hierarchy.length > 0) {
            const chartContainer = document.getElementById("employeeHierarchyChart");
            if (chartContainer) {
                chartContainer.innerHTML = '';
                const rootNode = result.employee_hierarchy.find(emp => !emp.pid);
                if (rootNode) {
                    try {
                        const chart = new OrgChart(chartContainer, {
                            template: "belinda",
                            layout: OrgChart.tree,
                            scaleInitial: 0.6,
                            enableDragDrop: false,
                            nodeBinding: {
                                field_0: "name",
                                field_1: "title",
                                img_0: "img"
                            },
                            nodes: result.employee_hierarchy
                        });
                    } catch (error) {
                        console.error("Error creating org chart:", error);
                        chartContainer.innerHTML = '<p>Error loading organizational chart</p>';
                    }
                } else {
                    console.error("No root node found");
                    chartContainer.innerHTML = '<p>Unable to display hierarchy: No root found</p>';
                }
            }
        } else {
            const chartContainer = document.getElementById("employeeHierarchyChart");
            if (chartContainer) {
                chartContainer.innerHTML = '<p>No hierarchy data available</p>';
            }
            console.log("No employee hierarchy data available");
        }
        if (result.is_manager) {
            const attendanceCanvas = document.getElementById("managerAttendanceChart");
            if (attendanceCanvas) {
                this.chartInstances.managerAttendanceChart = new Chart(attendanceCanvas, {
                    type: 'bar',
                    data: {
                        labels: ['Total', 'Men', 'Women'],
                        datasets: [{
                            label: 'Attendance (Total)',
                            data: [
                                result.manager_attendance.total,
                                result.manager_attendance.men,
                                result.manager_attendance.women
                            ],
                            backgroundColor: ['#71639e', '#36A2EB', '#FF6384'],
                        }]
                    },
                    options: {
                        responsive: true,
                        plugins: {
                            title: {
                                display: true,
                                text: 'Team Attendance Summary'
                            }
                        }
                    }
                });
            }
            const leaveCanvas = document.getElementById("managerLeaveChart");
            if (leaveCanvas) {
                this.chartInstances.managerLeaveChart = new Chart(leaveCanvas, {
                    type: 'bar',
                    data: {
                        labels: ['Total', 'Men', 'Women'],
                        datasets: [{
                            label: 'Leave (Total)',
                            data: [
                                result.manager_leaves.total,
                                result.manager_leaves.men,
                                result.manager_leaves.women
                            ],
                            backgroundColor: ['#71639e', '#36A2EB', '#FF6384'],
                        }]
                    },
                    options: {
                        responsive: true,
                        plugins: {
                            title: {
                                display: true,
                                text: 'Team Leave Summary'
                            }
                        }
                    }
                });
            }
            const projectCanvas = document.getElementById("managerProjectChart");
            if (projectCanvas) {
                this.chartInstances.managerProjectChart = new Chart(projectCanvas, {
                    type: 'pie',
                    data: {
                        labels: ['Completed Project', 'Remaining Project', 'Completed Task', 'Remaining Task'],
                        datasets: [{
                            data: [
                                result.manager_project_count.total_projects - result.manager_project_count.remaining_projects,
                                result.manager_project_count.remaining_projects,
                                result.manager_project_count.total_tasks - result.manager_project_count.remaining_tasks,
                                result.manager_project_count.remaining_tasks,
                            ],
                            backgroundColor: ['#36A2EB', '#4BC0C0', '#FFCE56', '#FF6384'],
                        }]
                    },
                    options: {
                        responsive: true,
                        plugins: {
                            title: {
                                display: true,
                                text: 'Team Project Summary'
                            }
                        }
                    }
                });
            }
        } else {
            const filterLabel = this._getFilterLabel();
            const attendanceCanvas = document.getElementById("attendanceChart");
            if (attendanceCanvas) {
                this.chartInstances.attendanceChart = new Chart(attendanceCanvas, {
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
                this.chartInstances.leaveChart = new Chart(leaveCanvas, {
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
    }

    onClickTotalProject() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Projects',
            res_model: 'project.project',
            views: [[false, 'list'], [false, 'form'], [false, 'kanban']],
            target: 'current',
        });
    }

    onClickTotalTask() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Tasks',
            res_model: 'project.task',
            views: [[false, 'list'], [false, 'form'], [false, 'kanban']],
            target: 'current',
        });
    }

    onClickRemainingProject() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Projects',
            res_model: 'project.project',
            domain: [['last_update_status', '!=', 'done']],
            views: [[false, 'list'], [false, 'form'], [false, 'kanban']],
            target: 'current',
        });
    }

    onClickRemainingTask() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Tasks',
            res_model: 'project.task',
            domain: [
                ["stage_id.name", "not in", ["Done", "Cancelled"]]
            ],
            views: [[false, 'list'], [false, 'form'], [false, 'kanban']],
            target: 'current',
        });
    }

    onClickAttendanceTotal() {
        const startDate = this.state.data.filter_start_date;
        const endDate = this.state.data.filter_end_date;
        const today = new Date().toISOString().split('T')[0];
        const domain = startDate && endDate
            ? [['check_in', '>=', startDate], ['check_in', '<=', endDate]]
            : [['check_in', '>=', today], ['check_in', '<=', today]];

        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Attendance',
            res_model: 'hr.attendance',
            domain: domain,
            views: [[false, 'list'], [false, 'form']],
            target: 'current',
        });
    }

    onClickAttendanceMen() {
        const startDate = this.state.data.filter_start_date;
        const endDate = this.state.data.filter_end_date;
        const today = new Date().toISOString().split('T')[0];
        const dateDomain = startDate && endDate
            ? [['check_in', '>=', startDate], ['check_in', '<=', endDate]]
            : [['check_in', '>=', today], ['check_in', '<=', today]];

        const genderDomain = [['employee_id.gender', '=', 'male']];
        const domain = [...dateDomain, ...genderDomain];
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Attendance (Male Employees)',
            res_model: 'hr.attendance',
            domain: domain,
            views: [[false, 'list'], [false, 'form']],
            target: 'current',
        });
    }

    onClickAttendanceWomen() {
        const startDate = this.state.data.filter_start_date;
        const endDate = this.state.data.filter_end_date;
        const today = new Date().toISOString().split('T')[0];
        const dateDomain = startDate && endDate
            ? [['check_in', '>=', startDate], ['check_in', '<=', endDate]]
            : [['check_in', '>=', today], ['check_in', '<=', today]];
        const genderDomain = [['employee_id.gender', '=', 'female']];
        const domain = [...dateDomain, ...genderDomain];

        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Attendance (Female Employees)',
            res_model: 'hr.attendance',
            domain: domain,
            views: [[false, 'list'], [false, 'form']],
            target: 'current',
        });
    }

    onClickLeaveTotal() {
        const startDate = this.state.data.filter_start_date;
        const endDate = this.state.data.filter_end_date;
        const today = new Date().toISOString().split('T')[0];
        const dateDomain = startDate && endDate
            ? [['request_date_from', '>=', startDate], ['request_date_to', '<=', endDate]]
            : [['request_date_from', '>=', today], ['request_date_to', '<=', today]];
        const stateDomain = [['state', '=', 'validate']];
        const domain = [...dateDomain, ...stateDomain];

        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Leave',
            res_model: 'hr.leave',
            domain: domain,
            views: [[false, 'list'], [false, 'form']],
            target: 'current',
        });
    }

    onClickLeaveMen() {
        const startDate = this.state.data.filter_start_date;
        const endDate = this.state.data.filter_end_date;
        const today = new Date().toISOString().split('T')[0];
        const dateDomain = startDate && endDate
            ? [['request_date_from', '>=', startDate], ['request_date_to', '<=', endDate]]
            : [['request_date_from', '>=', today], ['request_date_to', '<=', today]];
        const stateDomain = [['state', '=', 'validate']];
        const genderDomain = [['employee_id.gender', '=', 'male']];
        const domain = [...dateDomain, ...stateDomain, ...genderDomain];

        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Leave (Male Employees)',
            res_model: 'hr.leave',
            domain: domain,
            views: [[false, 'list'], [false, 'form']],
            target: 'current',
        });
    }

    onClickLeaveWomen() {
        const startDate = this.state.data.filter_start_date;
        const endDate = this.state.data.filter_end_date;
        const today = new Date().toISOString().split('T')[0];
        const dateDomain = startDate && endDate
            ? [['request_date_from', '>=', startDate], ['request_date_to', '<=', endDate]]
            : [['request_date_from', '>=', today], ['request_date_to', '<=', today]];
        const stateDomain = [['state', '=', 'validate']];
        const genderDomain = [['employee_id.gender', '=', 'female']];
        const domain = [...dateDomain, ...stateDomain, ...genderDomain];

        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Leave (Female Employees)',
            res_model: 'hr.leave',
            domain: domain,
            views: [[false, 'list'], [false, 'form']],
            target: 'current',
        });
    }
}

registry.category("actions").add("employee_dashboard_tag", Dashboard);