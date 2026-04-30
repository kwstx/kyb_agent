import axios, { AxiosInstance } from 'axios';
import WebSocket from 'isomorphic-ws';

export interface KYBRequest {
  company_name: string;
  jurisdiction: string;
  registration_number?: string;
  mode?: 'real_time' | 'batch';
  webhook_url?: string;
  metadata?: Record<string, any>;
}

export interface KYBResponse {
  request_id: string;
  status: string;
  profile?: any;
  error?: string;
}

export class KYBClient {
  private axiosInstance: AxiosInstance;
  private baseUrl: string;
  private wsUrl: string;

  constructor(baseUrl: string = 'http://localhost:8000') {
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.wsUrl = this.baseUrl.replace('http', 'ws');
    this.axiosInstance = axios.create({
      baseURL: this.baseUrl,
    });
  }

  async submitRequest(request: KYBRequest): Promise<string> {
    const response = await this.axiosInstance.post<KYBResponse>('/api/v1/kyb', request);
    return response.data.request_id;
  }

  async submitBatch(requests: KYBRequest[], webhookUrl?: string): Promise<{ batch_id: string; request_ids: string[] }> {
    const response = await this.axiosInstance.post('/api/v1/kyb/batch', {
      requests,
      webhook_url: webhookUrl,
    });
    return response.data;
  }

  streamInvestigation(requestId: string, onMessage: (data: any) => void): WebSocket {
    const ws = new WebSocket(`${this.wsUrl}/api/v1/ws/${requestId}`);
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data.toString());
      onMessage(data);
    };

    ws.onerror = (error) => {
      console.error('WebSocket Error:', error);
    };

    return ws;
  }

  async getStatus(requestId: string): Promise<KYBResponse> {
    const response = await this.axiosInstance.get<KYBResponse>(`/api/v1/status/${requestId}`);
    return response.data;
  }
}
