import { Outlet } from 'react-router-dom';

export function NetworkOverview() {
  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Networking</h1>
        <p className="text-gray-600">Network interfaces and proxy configurations</p>
      </div>
      <Outlet />
    </div>
  );
}
