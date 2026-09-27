import React, { useState, useEffect, useRef } from 'react';
import { Bell, Check, ExternalLink, RefreshCw, X } from 'lucide-react';
import { workflowApi } from '../../api/workflow';
import { Notification } from '../../types/workflow';
import { useNavigate } from 'react-router-dom';

export const NotificationBell: React.FC = () => {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const fetchNotifications = async () => {
    try {
      setLoading(true);
      const data = await workflowApi.listNotifications(false, 30);
      setNotifications(data);
    } catch (err) {
      console.error('Failed to load notifications', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 60000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const unreadCount = notifications.filter((n) => !n.read_at).length;

  const handleMarkRead = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await workflowApi.markNotificationRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, read_at: new Date().toISOString() } : n))
      );
    } catch (err) {
      console.error('Failed to mark notification read', err);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await workflowApi.markAllNotificationsRead();
      setNotifications((prev) =>
        prev.map((n) => ({ ...n, read_at: n.read_at || new Date().toISOString() }))
      );
    } catch (err) {
      console.error('Failed to mark all read', err);
    }
  };

  const handleNotificationClick = (n: Notification) => {
    if (!n.read_at) {
      workflowApi.markNotificationRead(n.id).catch(console.error);
      setNotifications((prev) =>
        prev.map((item) => (item.id === n.id ? { ...item, read_at: new Date().toISOString() } : item))
      );
    }
    if (n.related_entity_type === 'SERVICE_REQUEST' && n.related_entity_id) {
      setIsOpen(false);
      // Determine destination based on user context or general route
      navigate(`/workflows/requests/${n.related_entity_id}`);
    }
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 rounded-full text-gray-300 hover:text-white hover:bg-gray-800 transition focus:outline-none"
        title="Notifications"
        aria-label="Notifications"
      >
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 flex items-center justify-center min-w-[18px] h-[18px] px-1 text-[10px] font-bold text-white bg-blue-600 rounded-full border-2 border-gray-900">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-gray-900 border border-gray-800 rounded-xl shadow-2xl z-50 overflow-hidden text-sm">
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800 bg-gray-950">
            <div className="flex items-center space-x-2">
              <span className="font-semibold text-white">Notifications</span>
              {unreadCount > 0 && (
                <span className="px-2 py-0.5 text-xs bg-blue-900/60 text-blue-300 border border-blue-700/50 rounded-full">
                  {unreadCount} new
                </span>
              )}
            </div>
            <div className="flex items-center space-x-2">
              <button
                onClick={fetchNotifications}
                disabled={loading}
                className="p-1 text-gray-400 hover:text-white transition disabled:opacity-50"
                title="Refresh"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              </button>
              {unreadCount > 0 && (
                <button
                  onClick={handleMarkAllRead}
                  className="text-xs text-blue-400 hover:text-blue-300 hover:underline"
                >
                  Mark all read
                </button>
              )}
            </div>
          </div>

          <div className="max-h-96 overflow-y-auto divide-y divide-gray-800/60">
            {notifications.length === 0 ? (
              <div className="p-6 text-center text-gray-500">No notifications yet</div>
            ) : (
              notifications.map((n) => {
                const isUnread = !n.read_at;
                return (
                  <div
                    key={n.id}
                    onClick={() => handleNotificationClick(n)}
                    className={`p-3.5 hover:bg-gray-800/50 cursor-pointer transition flex items-start justify-between space-x-3 ${
                      isUnread ? 'bg-blue-950/20' : ''
                    }`}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2 mb-1">
                        <span
                          className={`w-2 h-2 rounded-full ${
                            isUnread ? 'bg-blue-500' : 'bg-transparent'
                          }`}
                        />
                        <h4 className="font-medium text-gray-200 truncate">{n.title}</h4>
                      </div>
                      <p className="text-xs text-gray-400 line-clamp-2 mb-1">{n.message}</p>
                      <div className="flex items-center space-x-3 text-[11px] text-gray-500">
                        <span>{new Date(n.created_at).toLocaleDateString()}</span>
                        <span>•</span>
                        <span className="uppercase text-[10px] tracking-wide text-gray-400">
                          {n.delivery_channel.replace('_', ' ')}
                        </span>
                      </div>
                    </div>
                    {isUnread && (
                      <button
                        onClick={(e) => handleMarkRead(n.id, e)}
                        className="p-1 rounded text-gray-400 hover:text-blue-400 hover:bg-gray-800 transition"
                        title="Mark as read"
                      >
                        <Check className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                );
              })
            )}
          </div>

          <div className="p-2 border-t border-gray-800 bg-gray-950/60 text-center">
            <button
              onClick={() => {
                setIsOpen(false);
                navigate('/notifications');
              }}
              className="text-xs text-blue-400 hover:text-blue-300 font-semibold cursor-pointer w-full py-1"
            >
              Open Notification Center →
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
