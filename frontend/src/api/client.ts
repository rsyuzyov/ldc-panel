/**
 * API Client for LDC Panel
 */

const API_BASE = '/api'

interface ApiError {
  detail: string
}

// Пути, которые обращаются к контроллеру домена (долгие операции)
const CONTROLLER_PATHS = ['/ad/', '/dns/', '/dhcp/', '/gpo', '/backup/']

// Глобальные колбэки для управления загрузкой
let onLoadingStart: ((message: string) => void) | null = null
let onLoadingStop: (() => void) | null = null

export function setLoadingCallbacks(
  start: (message: string) => void,
  stop: () => void
) {
  onLoadingStart = start
  onLoadingStop = stop
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

  private isControllerPath(path: string): boolean {
    return CONTROLLER_PATHS.some(p => path.includes(p))
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const showLoading = this.isControllerPath(path)
    
    if (showLoading && onLoadingStart) {
      onLoadingStart('Обращение к контроллеру домена...')
    }

    try {
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
    } finally {
      if (showLoading && onLoadingStop) {
        onLoadingStop()
      }
    }
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

  // AD Computers
  async getComputers(serverId: string, search?: string) {
    const params = new URLSearchParams({ server_id: serverId })
    if (search) params.append('search', search)
    return this.request<any[]>(`/ad/computers?${params}`)
  }

  // AD Service Accounts (MSA/gMSA)
  async getServiceAccounts(serverId: string) {
    const params = new URLSearchParams({ server_id: serverId })
    return this.request<any[]>(`/ad/service-accounts?${params}`)
  }

  async createUser(serverId: string, data: { username: string; fullName: string; email: string; groups: string; password?: string }) {
    // Преобразуем поля фронтенда в формат API
    const apiData = {
      sAMAccountName: data.username,
      cn: data.fullName || data.username,
      mail: data.email || undefined,
      password: data.password || 'TempPass123!',  // Временный пароль если не указан
    }
    return this.request<any>(`/ad/users?server_id=${serverId}`, {
      method: 'POST',
      body: JSON.stringify(apiData),
    })
  }

  async updateUser(serverId: string, username: string, data: { fullName?: string; email?: string; groups?: string }) {
    // Преобразуем поля фронтенда в формат API
    const apiData = {
      cn: data.fullName || undefined,
      mail: data.email || undefined,
    }
    return this.request<any>(`/ad/users/${username}?server_id=${serverId}`, {
      method: 'PATCH',
      body: JSON.stringify(apiData),
    })
  }

  async deleteUser(serverId: string, username: string) {
    return this.request(`/ad/users/${username}?server_id=${serverId}`, { method: 'DELETE' })
  }

  async changeUserPassword(serverId: string, userDnOrUsername: string, password: string) {
    return this.request<{ message: string }>(`/ad/users/${userDnOrUsername}/password?server_id=${serverId}`, {
      method: 'POST',
      body: JSON.stringify({ password }),
    })
  }

  // DNS
  async getDnsZones(serverId: string) {
    return this.request<any[]>(`/dns/zones?server_id=${serverId}`)
  }

  async getDnsRecords(serverId: string, zone: string) {
    return this.request<any[]>(`/dns/zones/${zone}/records?server_id=${serverId}`)
  }

  async getDnsAll(serverId: string) {
    return this.request<{ zones: any[]; records: any[]; currentZone: string | null }>(`/dns/all?server_id=${serverId}`)
  }

  async createDnsRecord(serverId: string, zone: string, data: { name: string; type: string; value: string; ttl: number }) {
    // Преобразуем value в data для бэкенда
    const apiData = {
      name: data.name,
      type: data.type,
      data: data.value,
      ttl: data.ttl,
    }
    return this.request<any>(`/dns/zones/${zone}/records?server_id=${serverId}`, {
      method: 'POST',
      body: JSON.stringify(apiData),
    })
  }

  async updateDnsRecord(serverId: string, zone: string, name: string, type: string, data: { value: string; ttl: number }) {
    return this.request<any>(`/dns/zones/${zone}/records/${name}/${type}?server_id=${serverId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  async deleteDnsRecord(serverId: string, zone: string, name: string, type: string, value?: string) {
    const params = new URLSearchParams({ server_id: serverId })
    if (value) params.append('value', value)
    return this.request(`/dns/zones/${zone}/records/${name}/${type}?${params}`, { method: 'DELETE' })
  }

  // DHCP
  async getDhcpSubnets(serverId: string) {
    return this.request<any[]>(`/dhcp/subnets?server_id=${serverId}`)
  }

  async getDhcpAll(serverId: string) {
    return this.request<{ subnets: any[]; reservations: any[]; leases: any[] }>(`/dhcp/all?server_id=${serverId}`)
  }

  async createDhcpSubnet(serverId: string, data: any) {
    return this.request<any>(`/dhcp/subnets?server_id=${serverId}`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async updateDhcpSubnet(serverId: string, subnetId: string, data: any) {
    return this.request<any>(`/dhcp/subnets/${subnetId}?server_id=${serverId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    })
  }

  async deleteDhcpSubnet(serverId: string, subnetId: string) {
    return this.request(`/dhcp/subnets/${subnetId}?server_id=${serverId}`, { method: 'DELETE' })
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
    // Преобразуем MAC в формат ID (lowercase с дефисами)
    const reservationId = mac.toLowerCase().replace(/:/g, '-')
    return this.request(`/dhcp/reservations/${reservationId}?server_id=${serverId}`, { method: 'DELETE' })
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
