import { useState, useEffect, useCallback } from 'react';
import { offlineStorage } from '../utils/offlineStorage';
import { surveyApi } from '../api/surveys';

export interface OnlineStatusHook {
  isOnline: boolean;
  isSyncing: boolean;
  pendingSyncCount: number;
  lastSyncError: string | null;
  syncNow: () => Promise<void>;
  refreshPendingCount: () => Promise<void>;
}

export function useOnlineStatus(): OnlineStatusHook {
  const [isOnline, setIsOnline] = useState<boolean>(
    typeof navigator !== 'undefined' ? navigator.onLine : true
  );
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [pendingSyncCount, setPendingSyncCount] = useState<number>(0);
  const [lastSyncError, setLastSyncError] = useState<string | null>(null);

  const refreshPendingCount = useCallback(async () => {
    try {
      const pending = await offlineStorage.getPendingSyncOperations();
      setPendingSyncCount(pending.length);
    } catch {
      setPendingSyncCount(0);
    }
  }, []);

  const syncNow = useCallback(async () => {
    if (!isOnline || isSyncing) return;

    try {
      setIsSyncing(true);
      setLastSyncError(null);

      const pending = await offlineStorage.getPendingSyncOperations();
      if (pending.length === 0) {
        setIsSyncing(false);
        return;
      }

      const response = await surveyApi.batchSync(pending);

      // Process results and remove successfully synced operations
      for (const res of response.results) {
        if (res.status === 'SYNCED') {
          await offlineStorage.removeSyncOperation(res.client_operation_id);
        } else if (res.status === 'CONFLICT') {
          setLastSyncError(`Conflict on operation ${res.client_operation_id}: ${res.error || 'Concurrent modification'}`);
        } else if (res.status === 'FAILED') {
          setLastSyncError(`Sync failed: ${res.error || 'Server error'}`);
        }
      }

      await refreshPendingCount();
    } catch (err: any) {
      setLastSyncError(err?.message || 'Network error during synchronization');
    } finally {
      setIsSyncing(false);
    }
  }, [isOnline, isSyncing, refreshPendingCount]);

  useEffect(() => {
    refreshPendingCount();

    const handleOnline = () => {
      setIsOnline(true);
      // Auto-trigger sync when connectivity returns
      syncNow();
    };

    const handleOffline = () => {
      setIsOnline(false);
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Periodic check for pending count
    const interval = setInterval(refreshPendingCount, 5000);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      clearInterval(interval);
    };
  }, [refreshPendingCount, syncNow]);

  return {
    isOnline,
    isSyncing,
    pendingSyncCount,
    lastSyncError,
    syncNow,
    refreshPendingCount,
  };
}
