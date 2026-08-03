import { API_BASE_URL } from '../../apiConfig';

export const loadOperationsWorkspace = async (apiCall) => (
  apiCall(`${API_BASE_URL}/operations/workspace`, { method: 'GET' })
);
