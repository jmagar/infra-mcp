import { createBrowserRouter } from 'react-router-dom';

function SimpleTest() {
  return (
    <div style={{ padding: '20px', fontFamily: 'Arial' }}>
      <h1>Ultra Simple Test</h1>
      <p>If you see this, the basic router works</p>
      <p>Time: {new Date().toISOString()}</p>
    </div>
  );
}

export const minimal2Router = createBrowserRouter([
  {
    path: '/',
    element: <SimpleTest />,
  },
]);