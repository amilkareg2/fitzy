import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { App } from './App';
import { renderWithProviders } from './test/render';

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('App shell', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ status: 'ok' })));
  });

  it('renders the four bottom tabs in order', () => {
    renderWithProviders(<App />);

    const nav = screen.getByRole('navigation', { name: 'Main' });
    const links = within(nav).getAllByRole('link');
    expect(links.map((link) => link.textContent)).toEqual([
      'Today',
      'Calendar',
      'Progress',
      'Coach',
    ]);
    expect(within(nav).getByRole('link', { name: 'Today' })).toHaveAttribute(
      'aria-current',
      'page',
    );
  });

  it('switches page when a tab is tapped', async () => {
    const user = userEvent.setup();
    renderWithProviders(<App />);

    await user.click(screen.getByRole('link', { name: 'Progress' }));

    expect(screen.getByRole('heading', { level: 1, name: 'Progress' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Progress' })).toHaveAttribute('aria-current', 'page');
  });

  it('sends unknown routes to Today', () => {
    renderWithProviders(<App />, { route: '/nope' });

    expect(screen.getByRole('link', { name: 'Today' })).toHaveAttribute('aria-current', 'page');
  });
});

describe('API status on Today', () => {
  it('shows "API ok" when /health answers', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ status: 'ok' }));
    vi.stubGlobal('fetch', fetchMock);

    renderWithProviders(<App />);

    expect(await screen.findByText('API ok')).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith('/api/health', expect.anything());
  });

  it('shows "API unreachable" when fetch fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));

    renderWithProviders(<App />);

    expect(screen.getByRole('status')).toHaveTextContent('Checking API');
    expect(await screen.findByText('API unreachable')).toBeInTheDocument();
  });

  it('shows "API unreachable" when the API returns an error status', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ detail: 'down' }, 503)));

    renderWithProviders(<App />);

    expect(await screen.findByText('API unreachable')).toBeInTheDocument();
  });
});
