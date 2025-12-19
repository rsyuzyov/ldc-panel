/**
 * API Client for LDC Panel
 */

const API_BASE = '/api'

interface ApiError {
  detail: string
}

class ApiClient {
  private token: string | null = null

  setToken(token: string | null) {
    this.token = token
    if (token) {
      localStorage.setItem('ldc_token', token)
    } else {
      localStorage.removeItem('ldc_token')
    }
  }

  getToken(): string | null {
    if (!this.token) {
      this.token = localStorage.getItem('ldc_token')
    }
    return this.token
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    }

    const token = this.getToken()
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
    })

    if (!response.ok) {
      const error: ApiError = await response.json().catch(() => ({ detail: 'Ошибка сервера' }))
      throw new Error(error.detail)
    }

    return response.json()
  }

  // Auth
  async login(username: string, password: string) {
    const data = await this.request<{ token: string; ttl: number; username: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    })
    this.setToken(data.token)
    return data
  }

  async logout() {
    await this.request('/auth/logout', { method: 'POST' })
    this.setToken(null)
  }

  async getMe() {
    return this.request<{ username: string }>('/auth/me')
  }

  // Servers
  async getServers() {
    return this.request<any[]>('/servers')
  }

  async createServer(data: FormData) {
    const token = this.getToken()
    const response = await fetch(`${API_BASE}/servers`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: data,
    })
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Ошибка' }))
      throw new Error(error.detail)
    }
    return response.json()
  }

  async deleteServer(id: string) {
    return this.request(`/servers/${id}`, { method: 'DELETE' })
  }

  async updateServer(id: string, data: FormData) {
    const token = this.getToken()
    const response = await fetch(`${API_BASE}/servers/${id}`, {
      method: 'PUT',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: data,
    })
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Ошибка' }))
      throw new Error(error.detail)
    }
    return response.json()
  }

  async testServer(id: string) {
    return this.request<{ success: boolean; error?: string; services: any }>(`/servers/${id}/test`, { method: 'POST' })
  }

  // AD Users
  async getUsers(serverId: string, search?: string) {
    const params = new URLSearchParams({ server_id: serverId })
    if (search) params.append('search', search)
    return this.request<any[]>(`/ad/users?${params}`)
  }

  async createUser(serverId: string, data: { username: string; fullName: string; email: string; groups: string }) {
    return this.request<any>(`/ad/users?server_id=${serverId}`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async updateUser(serverId: string, username: string, data: { fullName?: string; email?: string; groups?: string }) {
    return this.request<any>(`/ad/users/${username}?server_id=${serverId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  async deleteUser(serverId: string, username: string) {
    return this.request(`/ad/users/${username}?server_id=${serverId}`, { method: 'DELETE' })
  }

  // DNS
  async getDnsZones(serverId: string) {
    return this.request<any[]>(`/dns/zones?server_id=${serverId}`)
  }

  async getDnsRecords(serverId: string, zone: string) {
    return this.request<any[]>(`/dns/zones/${zone}/records?server_id=${serverId}`)
  }

  async createDnsRecord(serverId: string, zone: string, data: { name: string; type: string; value: string; ttl: number }) {
    return this.request<any>(`/dns/zones/${zone}/records?server_id=${serverId}`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async updateDnsRecord(serverId: string, zone: string, name: string, type: string, data: { value: string; ttl: number }) {
    return this.request<any>(`/dns/zones/${zone}/records/${name}/${type}?server_id=${serverId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  async deleteDnsRecord(serverId: string, zone: string, name: string, type: string) {
    return this.request(`/dns/zones/${zone}/records/${name}/${type}?server_id=${serverId}`, { method: 'DELETE' })
  }

  // DHCP
  async getDhcpSubnets(serverId: string) {
    return this.request<any[]>(`/dhcp/subnets?server_id=${serverId}`)
  }

  async getDhcpReservations(serverId: string) {
    return this.request<any[]>(`/dhcp/reservations?server_id=${serverId}`)
  }

  async getDhcpLeases(serverId: string) {
    return this.request<any[]>(`/dhcp/leases?server_id=${serverId}`)
  }

  async createDhcpReservation(serverId: string, data: { hostname: string; mac: string; ip: string; description?: string }) {
    return this.request<any>(`/dhcp/reservations?server_id=${serverId}`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async deleteDhcpReservation(serverId: string, mac: string) {
    return this.request(`/dhcp/reservations/${mac}?server_id=${serverId}`, { method: 'DELETE' })
  }

  // GPO
  async getGpos(serverId: string) {
    return this.request<any[]>(`/gpo?server_id=${serverId}`)
  }

  // Logs
  async getLogs(limit = 100) {
    return this.request<any[]>(`/logs?limit=${limit}`)
  }

  // Backup
  async getBackups(serverId: string) {
    return this.request<any[]>(`/backup/list?server_id=${serverId}`)
  }

  async backupLdif(serverId: string) {
    return this.request<{ message: string; filename: string }>(`/backup/ldif?server_id=${serverId}`, { method: 'POST' })
  }

  async backupDhcp(serverId: string) {
    return this.request<{ message: string; filename: string }>(`/backup/dhcp?server_id=${serverId}`, { method: 'POST' })
  }

  async restoreBackup(serverId: string, type: string, filename: string) {
    return this.request<{ message: string }>(`/backup/restore/${type}/${filename}?server_id=${serverId}`, { method: 'POST' })
  }
}

export const api = new ApiClient()
