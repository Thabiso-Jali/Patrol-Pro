import { useCallback, useEffect, useState } from 'react';

import { pageFromPath, pathForPage } from './rbac';

export const usePageNavigation = (isAuthenticated, visibleNavItems) => {
  const [activeNav, setActiveNav] = useState(() => pageFromPath(window.location.pathname));
  const navigateToPage = useCallback((pageId, { replace = false } = {}) => {
    window.history[replace ? 'replaceState' : 'pushState']({}, '', pathForPage(pageId));
    setActiveNav(pageId);
  }, []);

  useEffect(() => {
    if (!isAuthenticated) return;
    const activeExists = visibleNavItems.some((item) => item.id === activeNav);
    const explicitlyRequested = pageFromPath(window.location.pathname) === activeNav
      && window.location.pathname !== '/';
    if (!activeExists && !explicitlyRequested && visibleNavItems.length > 0) {
      navigateToPage(visibleNavItems[0].id, { replace: true });
    }
  }, [isAuthenticated, activeNav, visibleNavItems, navigateToPage]);

  useEffect(() => {
    const handlePopState = () => setActiveNav(pageFromPath(window.location.pathname));
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  return { activeNav, navigateToPage };
};
