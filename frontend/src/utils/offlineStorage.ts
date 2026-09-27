import {
  SurveyAssignment,
  SurveyObservation,
  SurveySession,
  SyncOperationItem,
} from '../types';

const DB_NAME = 'GeoVertexFieldCadastreDB';
const DB_VERSION = 1;

class OfflineStorage {
  private dbPromise: Promise<IDBDatabase> | null = null;

  private getDB(): Promise<IDBDatabase> {
    if (typeof window === 'undefined' || !window.indexedDB) {
      return Promise.reject(new Error('IndexedDB is not available in this environment'));
    }

    if (this.dbPromise) {
      return this.dbPromise;
    }

    this.dbPromise = new Promise((resolve, reject) => {
      const request = window.indexedDB.open(DB_NAME, DB_VERSION);

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result;

        if (!db.objectStoreNames.contains('assignments')) {
          db.createObjectStore('assignments', { keyPath: 'id' });
        }
        if (!db.objectStoreNames.contains('sessions')) {
          db.createObjectStore('sessions', { keyPath: 'id' });
        }
        if (!db.objectStoreNames.contains('observations')) {
          const obsStore = db.createObjectStore('observations', { keyPath: 'id' });
          obsStore.createIndex('session_id', 'session_id', { unique: false });
        }
        if (!db.objectStoreNames.contains('sync_queue')) {
          db.createObjectStore('sync_queue', { keyPath: 'client_operation_id' });
        }
      };

      request.onsuccess = () => {
        resolve(request.result);
      };

      request.onerror = () => {
        reject(request.error);
      };
    });

    return this.dbPromise;
  }

  // --- Assignments ---
  async cacheAssignments(assignments: SurveyAssignment[]): Promise<void> {
    try {
      const db = await this.getDB();
      const tx = db.transaction('assignments', 'readwrite');
      const store = tx.objectStore('assignments');
      for (const a of assignments) {
        store.put(a);
      }
      return new Promise((resolve, reject) => {
        tx.oncomplete = () => resolve();
        tx.onerror = () => reject(tx.error);
      });
    } catch {
      // Fallback: localStorage
      localStorage.setItem('offline_assignments', JSON.stringify(assignments));
    }
  }

  async getLocalAssignments(): Promise<SurveyAssignment[]> {
    try {
      const db = await this.getDB();
      const tx = db.transaction('assignments', 'readonly');
      const store = tx.objectStore('assignments');
      const request = store.getAll();
      return new Promise((resolve, reject) => {
        request.onsuccess = () => resolve(request.result || []);
        request.onerror = () => reject(request.error);
      });
    } catch {
      const data = localStorage.getItem('offline_assignments');
      return data ? JSON.parse(data) : [];
    }
  }

  async getLocalAssignment(id: string): Promise<SurveyAssignment | null> {
    try {
      const db = await this.getDB();
      const tx = db.transaction('assignments', 'readonly');
      const store = tx.objectStore('assignments');
      const request = store.get(id);
      return new Promise((resolve, reject) => {
        request.onsuccess = () => resolve(request.result || null);
        request.onerror = () => reject(request.error);
      });
    } catch {
      const list = await this.getLocalAssignments();
      return list.find((a) => a.id === id) || null;
    }
  }

  // --- Sessions ---
  async cacheSession(session: SurveySession): Promise<void> {
    try {
      const db = await this.getDB();
      const tx = db.transaction('sessions', 'readwrite');
      tx.objectStore('sessions').put(session);
      return new Promise((resolve, reject) => {
        tx.oncomplete = () => resolve();
        tx.onerror = () => reject(tx.error);
      });
    } catch {
      localStorage.setItem(`offline_session_${session.id}`, JSON.stringify(session));
    }
  }

  async getLocalSession(id: string): Promise<SurveySession | null> {
    try {
      const db = await this.getDB();
      const tx = db.transaction('sessions', 'readonly');
      const request = tx.objectStore('sessions').get(id);
      return new Promise((resolve, reject) => {
        request.onsuccess = () => resolve(request.result || null);
        request.onerror = () => reject(request.error);
      });
    } catch {
      const data = localStorage.getItem(`offline_session_${id}`);
      return data ? JSON.parse(data) : null;
    }
  }

  // --- Observations ---
  async saveDraftObservation(obs: SurveyObservation): Promise<void> {
    try {
      const db = await this.getDB();
      const tx = db.transaction('observations', 'readwrite');
      tx.objectStore('observations').put(obs);
      return new Promise((resolve, reject) => {
        tx.oncomplete = () => resolve();
        tx.onerror = () => reject(tx.error);
      });
    } catch {
      const existing = await this.getLocalObservations(obs.session_id);
      const filtered = existing.filter((o) => o.id !== obs.id);
      filtered.push(obs);
      localStorage.setItem(`offline_observations_${obs.session_id}`, JSON.stringify(filtered));
    }
  }

  async getLocalObservations(sessionId: string): Promise<SurveyObservation[]> {
    try {
      const db = await this.getDB();
      const tx = db.transaction('observations', 'readonly');
      const store = tx.objectStore('observations');
      const index = store.index('session_id');
      const request = index.getAll(sessionId);
      return new Promise((resolve, reject) => {
        request.onsuccess = () => resolve(request.result || []);
        request.onerror = () => reject(request.error);
      });
    } catch {
      const data = localStorage.getItem(`offline_observations_${sessionId}`);
      return data ? JSON.parse(data) : [];
    }
  }

  // --- Sync Queue ---
  async enqueueSyncOperation(op: SyncOperationItem): Promise<void> {
    try {
      const db = await this.getDB();
      const tx = db.transaction('sync_queue', 'readwrite');
      tx.objectStore('sync_queue').put(op);
      return new Promise((resolve, reject) => {
        tx.oncomplete = () => resolve();
        tx.onerror = () => reject(tx.error);
      });
    } catch {
      const queue = await this.getPendingSyncOperations();
      queue.push(op);
      localStorage.setItem('offline_sync_queue', JSON.stringify(queue));
    }
  }

  async getPendingSyncOperations(): Promise<SyncOperationItem[]> {
    try {
      const db = await this.getDB();
      const tx = db.transaction('sync_queue', 'readonly');
      const request = tx.objectStore('sync_queue').getAll();
      return new Promise((resolve, reject) => {
        request.onsuccess = () => resolve(request.result || []);
        request.onerror = () => reject(request.error);
      });
    } catch {
      const data = localStorage.getItem('offline_sync_queue');
      return data ? JSON.parse(data) : [];
    }
  }

  async removeSyncOperation(clientOpId: string): Promise<void> {
    try {
      const db = await this.getDB();
      const tx = db.transaction('sync_queue', 'readwrite');
      tx.objectStore('sync_queue').delete(clientOpId);
      return new Promise((resolve, reject) => {
        tx.oncomplete = () => resolve();
        tx.onerror = () => reject(tx.error);
      });
    } catch {
      const queue = await this.getPendingSyncOperations();
      const filtered = queue.filter((item) => item.client_operation_id !== clientOpId);
      localStorage.setItem('offline_sync_queue', JSON.stringify(filtered));
    }
  }

  async clearSyncQueue(): Promise<void> {
    try {
      const db = await this.getDB();
      const tx = db.transaction('sync_queue', 'readwrite');
      tx.objectStore('sync_queue').clear();
      return new Promise((resolve, reject) => {
        tx.oncomplete = () => resolve();
        tx.onerror = () => reject(tx.error);
      });
    } catch {
      localStorage.removeItem('offline_sync_queue');
    }
  }
}

export const offlineStorage = new OfflineStorage();
