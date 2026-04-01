import { render, screen } from '@testing-library/react';
import { AudioPlayer } from '../components/AudioPlayer';

test('renders audio player status', () => {
  const mockWs = {
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
  };
  
  render(<AudioPlayer ws={mockWs} isConnected={true} />);
  
  expect(screen.getByText(/Audio:/)).toBeInTheDocument();
  expect(screen.getByText(/Chunks:/)).toBeInTheDocument();
});
