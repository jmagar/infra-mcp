import { Outlet } from 'react-router-dom';

export function StorageOverview() {
  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Storage</h1>
        <p className="text-gray-600">ZFS pools, datasets, and drive health</p>
      </div>
      <Outlet />
    </div>
  );
}