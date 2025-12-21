/**
 * Frontend Logger with backend integration
 * 
 * Sends logs to backend for centralized logging and analysis
 */

interface LogContext {
    [key: string]: any
}

interface LogEntry {
    level: 'error' | 'warn' | 'info' | 'debug'
    message: string
    context?: LogContext
    timestamp: string
    url: string
}

class Logger {
    private static batch: LogEntry[] = []
    private static batchTimer: number | null = null
    private static readonly BATCH_SIZE = 10
    private static readonly BATCH_TIMEOUT = 5000 // 5 seconds
    private static readonly MAX_LOCAL_LOGS = 100

    /**
     * Send logs to backend
     */
    private static async sendToBackend(entries: LogEntry[]): Promise<void> {
        if (entries.length === 0) return

        try {
            const token = localStorage.getItem('ldc_token')
            const headers: Record<string, string> = {
                'Content-Type': 'application/json',
            }

            if (token) {
                headers['Authorization'] = `Bearer ${token}`
            }

            await fetch('/api/logs/frontend/batch', {
                method: 'POST',
                headers,
                body: JSON.stringify(entries),
            })
        } catch (err) {
            // Fallback to localStorage if backend is unavailable
            this.saveToLocalStorage(entries)
            console.warn('Failed to send logs to backend, saved to localStorage', err)
        }
    }

    /**
     * Save logs to localStorage as fallback
     */
    private static saveToLocalStorage(entries: LogEntry[]): void {
        try {
            const stored = localStorage.getItem('ldc_logs')
            const logs = stored ? JSON.parse(stored) : []
            logs.push(...entries)

            // Keep only last MAX_LOCAL_LOGS
            const trimmed = logs.slice(-this.MAX_LOCAL_LOGS)
            localStorage.setItem('ldc_logs', JSON.stringify(trimmed))
        } catch (err) {
            console.warn('Failed to save logs to localStorage', err)
        }
    }

    /**
     * Add log to batch and schedule sending
     */
    private static addToBatch(entry: LogEntry): void {
        this.batch.push(entry)

        // Send immediately for errors
        if (entry.level === 'error') {
            this.flushBatch()
            return
        }

        // Send if batch is full
        if (this.batch.length >= this.BATCH_SIZE) {
            this.flushBatch()
            return
        }

        // Schedule batch send
        if (this.batchTimer === null) {
            this.batchTimer = window.setTimeout(() => {
                this.flushBatch()
            }, this.BATCH_TIMEOUT)
        }
    }

    /**
     * Flush current batch
     */
    private static flushBatch(): void {
        if (this.batchTimer !== null) {
            clearTimeout(this.batchTimer)
            this.batchTimer = null
        }

        if (this.batch.length > 0) {
            const toSend = [...this.batch]
            this.batch = []
            this.sendToBackend(toSend)
        }
    }

    /**
     * Create log entry
     */
    private static createEntry(
        level: LogEntry['level'],
        message: string,
        contextOrError?: LogContext | Error
    ): LogEntry {
        const entry: LogEntry = {
            level,
            message,
            timestamp: new Date().toISOString(),
            url: window.location.href,
        }

        if (contextOrError) {
            if (contextOrError instanceof Error) {
                entry.context = {
                    errorName: contextOrError.name,
                    errorMessage: contextOrError.message,
                    stack: contextOrError.stack,
                }
            } else {
                entry.context = contextOrError
            }
        }

        return entry
    }

    /**
     * Log error
     */
    static error(message: string, error?: Error | LogContext): void {
        const entry = this.createEntry('error', message, error)
        this.addToBatch(entry)

        // Also log to console in development
        if (import.meta.env.DEV) {
            console.error(message, error)
        }
    }

    /**
     * Log warning
     */
    static warn(message: string, context?: LogContext): void {
        const entry = this.createEntry('warn', message, context)
        this.addToBatch(entry)

        if (import.meta.env.DEV) {
            console.warn(message, context)
        }
    }

    /**
     * Log info
     */
    static info(message: string, context?: LogContext): void {
        const entry = this.createEntry('info', message, context)
        this.addToBatch(entry)

        if (import.meta.env.DEV) {
            console.log(message, context)
        }
    }

    /**
     * Log debug (only in development)
     */
    static debug(message: string, context?: LogContext): void {
        if (import.meta.env.DEV) {
            const entry = this.createEntry('debug', message, context)
            this.addToBatch(entry)
            console.log(message, context)
        }
    }
}

// Flush logs before page unload
window.addEventListener('beforeunload', () => {
    Logger['flushBatch']()
})

export default Logger
