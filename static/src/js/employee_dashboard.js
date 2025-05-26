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

        // Attendance Info
        document.getElementById('my_attendance').innerHTML = `
            <div><strong>This Month:</strong> ${result.my_attendance.toFixed(2)} hrs</div>
            <div><strong>Today:</strong> ${result.hours_today.toFixed(2)} hrs</div>
            <div><strong>Ongoing:</strong> ${result.last_attendance_worked_hours.toFixed(2)} hrs</div>
            <div><strong>Status:</strong> ${result.attendance_state === 'checked_in' ? '✔️ Checked In' : '❌ Checked Out'}</div>
            <div><strong>Last In:</strong> ${result.last_check_in || '-'}</div>
            <div><strong>Last Out:</strong> ${result.last_check_out || '-'}</div>
            <div><strong>Overtime:</strong> ${result.total_overtime.toFixed(2)} hrs</div>
        `;

        // Leave Info
        document.getElementById('my_leaves').innerHTML = `
            <div><strong>Total Leaves Taken:</strong> ${result.total_leaves_taken.toFixed(1)} days</div>
            <div><strong>Leaves This Month:</strong> ${result.leaves_this_month.toFixed(1)} days</div>
            <div><strong>Pending Leave Requests:</strong> ${result.pending_leaves_count}</div>
        `;
    }


}
EmployeeDashboard.template = "employee_dashboard.EmployeeDashboard";
registry.category("actions").add("employee_dashboard_tag", EmployeeDashboard);
