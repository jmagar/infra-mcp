import { Outlet } from 'react-router-dom';

export function SystemOverview() {
  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">System</h1>
        <p className="text-gray-600">System updates, backups, and VM management</p>
      </div>
      <Outlet />
    </div>
  );
}
