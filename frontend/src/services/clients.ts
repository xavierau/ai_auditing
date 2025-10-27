/**
 * Clients API Service
 *
 * API functions for client management endpoints.
 */

import { apiClient } from './api';

/**
 * Client data types
 */
export interface Client {
  id: number;
  company_name: string;
  registration_number?: string;
  industry?: string;
}

export interface ClientCreate {
  company_name: string;
  registration_number?: string;
  address?: string;
  industry?: string;
  contact_person?: string;
  contact_email?: string;
  contact_phone?: string;
}

/**
 * ClientsAPI - CRUD operations for clients
 */
export class ClientsAPI {
  /**
   * Get all clients for current tenant
   *
   * @example
   * const clients = await ClientsAPI.list()
   */
  static async list(skip = 0, limit = 100): Promise<Client[]> {
    return apiClient.get<Client[]>('/api/v1/projects/clients', {
      params: { skip, limit },
    });
  }

  /**
   * Create new client
   *
   * @example
   * const client = await ClientsAPI.create({
   *   company_name: 'ABC Company Ltd',
   *   registration_number: '12345678',
   *   industry: 'Technology',
   * })
   */
  static async create(data: ClientCreate): Promise<Client> {
    return apiClient.post<Client>('/api/v1/projects/clients', data);
  }
}
