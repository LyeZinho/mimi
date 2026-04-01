import { render, screen } from '@testing-library/react';
import { AvatarSync } from '../components/AvatarSync';

test('renders avatar sync status', () => {
  const mockWs = {
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
  };
  
  render(<AvatarSync ws={mockWs} isConnected={true} vrm={null} />);
  
  expect(screen.getByText(/Phoneme:/)).toBeInTheDocument();
});
