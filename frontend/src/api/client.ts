/**
 * API клиент на основе Axios
 */

import axios, { type AxiosInstance, type AxiosRequestConfig, type AxiosResponse } from 'axios';
import type { ApiError } from '../types';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors() {
    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        // Добавляем timestamp для кэш-бастинга
        if (config.method === 'get') {
          config.params = {
            ...config.params,
            _t: Date.now(),
          };
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response: AxiosResponse) => {
        return response;
      },
      (error) => {
        // Обработка ошибок
        if (error.response) {
          const apiError: ApiError = {
            detail: error.response.data?.detail || 'Unknown error',
            status_code: error.response.status,
          };
          return Promise.reject(apiError);
        } else if (error.request) {
          const apiError: ApiError = {
            detail: 'Network error - no response received',
            status_code: 0,
          };
          return Promise.reject(apiError);
        } else {
          const apiError: ApiError = {
            detail: error.message || 'Request setup error',
            status_code: 0,
          };
          return Promise.reject(apiError);
        }
      }
    );
  }

  // Generic methods with AbortSignal support
  async get<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.get<T>(url, config);
    return response.data;
  }

  async post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.post<T>(url, data, config);
    return response.data;
  }

  async put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.put<T>(url, data, config);
    return response.data;
  }

  async delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.delete<T>(url, config);
    return response.data;
  }

  /**
   * Creates an AbortController and returns it with the signal
   * Use this for cancellable requests
   */
  createAbortController(): AbortController {
    return new AbortController();
  }

  /**
   * Cancellable GET request
   * @param url - API endpoint
   * @param signal - AbortSignal for cancellation
   * @param config - Additional axios config
   */
  async getCancellable<T = any>(
    url: string,
    signal?: AbortSignal,
    config?: AxiosRequestConfig
  ): Promise<T> {
    const response = await this.client.get<T>(url, {
      ...config,
      signal,
    });
    return response.data;
  }

  /**
   * Cancellable POST request
   */
  async postCancellable<T = any>(
    url: string,
    data?: any,
    signal?: AbortSignal,
    config?: AxiosRequestConfig
  ): Promise<T> {
    const response = await this.client.post<T>(url, data, {
      ...config,
      signal,
    });
    return response.data;
  }

  // Health check
  async healthCheck() {
    return this.get('/api/health');
  }
}

// Singleton instance
export const apiClient = new ApiClient();
export default apiClient;
