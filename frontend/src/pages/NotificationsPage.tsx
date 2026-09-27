import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Bell,
  Check,
  CheckCheck,
  RefreshCw,
  Settings,
  AlertTriangle,
  Info,
  CheckCircle,
  AlertOctagon,
  ExternalLink,
  ShieldAlert,
} from 'lucide-react';
import { notificationApi } from '../api/governance';
import { NotificationItem, NotificationPreferenceItem } from '../types/governance';

export const NotificationsPage: React.FC = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'inbox' | 'preferences'>('inbox');
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [total, setTotal] = useState(0);
  const [preferences, setPreferences] = useState<NotificationPreferenceItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchNotifications = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await notificationApi.listNotifications(unreadOnly, undefined, 1, 50);
      setNotifications(res.items);
      setTotal(res.total);
    } catch (err: any) {
      setError(err.message || 'Failed to load notifications');
    } finally {
      setLoading(false);
    }
  };

  const fetchPreferences = async () => {
    try {
      const prefs = await notificationApi.getPreferences();
      setPreferences(prefs);
    } catch (err: any) {
      console.error('Failed to load notification preferences', err);
    }
  };

  useEffect(() => {
    if (activeTab === 'inbox') {
      fetchNotifications();
    } else {
      fetchPreferences();
    }
  }, [activeTab, unreadOnly]);

  const handleMarkRead = async (id: string) => {
    try {
      await notificationApi.markAsRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, read_at: new Date().toISOString() } : n))
      );
    } catch (err) {
      console.error(err);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await notificationApi.markAllAsRead();
      setNotifications((prev) =>
        prev.map((n) => ({ ...n, read_at: n.read_at || new Date().toISOString() }))
      );
    } catch (err) {
      console.error(err);
    }
  };

  const handleTogglePreference = async (
    notificationType: string,
    channel: string,
    currentEnabled: boolean
  ) => {
    try {
      const updated = await notificationApi.updatePreference({
        notification_type: notificationType,
        channel,
        enabled: !currentEnabled,
      });
      setPreferences((prev) =>
        prev.map((p) =>
          p.notification_type === notificationType && p.channel === channel ? updated : p
        )
      );
    } catch (err: any) {
      alert(err.message || 'Failed to update preference');
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono font-medium bg-blue-950/60 border border-blue-800 text-blue-300">
              Notification Center
            </span>
          </div>
          <h1 className="text-2xl font-bold text-white mt-1">Platform Notifications & Alerts</h1>
          <p className="text-sm text-slate-400">
            Real-time cadastral workflow alerts, topology notices, and delivery channel preferences.
          </p>
        </div>

        <div className="flex items-center space-x-2 self-start sm:self-auto">
          {activeTab === 'inbox' && (
            <button
              onClick={handleMarkAllRead}
              className="px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:border-slate-700 flex items-center space-x-1.5 text-xs font-semibold transition cursor-pointer"
            >
              <CheckCheck className="w-3.5 h-3.5 text-blue-400" />
              <span>Mark All Read</span>
            </button>
          )}
          <button
            onClick={() => (activeTab === 'inbox' ? fetchNotifications() : fetchPreferences())}
            disabled={loading}
            className="px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:border-slate-700 flex items-center space-x-1.5 text-xs font-semibold transition cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-950/50 border border-rose-800/80 text-rose-300 text-xs flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
          <span>{error}</span>
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center space-x-2 border-b border-slate-800 pb-2">
        <button
          onClick={() => setActiveTab('inbox')}
          className={`px-4 py-2 rounded-xl text-xs font-semibold transition cursor-pointer ${
            activeTab === 'inbox'
              ? 'bg-blue-600 text-white shadow-lg shadow-blue-950'
              : 'text-slate-400 hover:text-white bg-slate-900/60'
          }`}
        >
          Notification Inbox
        </button>
        <button
          onClick={() => setActiveTab('preferences')}
          className={`px-4 py-2 rounded-xl text-xs font-semibold flex items-center space-x-1.5 transition cursor-pointer ${
            activeTab === 'preferences'
              ? 'bg-blue-600 text-white shadow-lg shadow-blue-950'
              : 'text-slate-400 hover:text-white bg-slate-900/60'
          }`}
        >
          <Settings className="w-3.5 h-3.5" />
          <span>Channel Preferences</span>
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'inbox' ? (
        <div className="space-y-4">
          {/* Sub-filter */}
          <div className="flex items-center space-x-2 text-xs">
            <button
              onClick={() => setUnreadOnly(false)}
              className={`px-3 py-1 rounded-lg transition cursor-pointer ${
                !unreadOnly ? 'bg-slate-800 text-white font-semibold' : 'text-slate-400 hover:text-white'
              }`}
            >
              All Notifications ({total})
            </button>
            <button
              onClick={() => setUnreadOnly(true)}
              className={`px-3 py-1 rounded-lg transition cursor-pointer ${
                unreadOnly ? 'bg-slate-800 text-white font-semibold' : 'text-slate-400 hover:text-white'
              }`}
            >
              Unread Only
            </button>
          </div>

          {/* Notifications List */}
          {loading && notifications.length === 0 ? (
            <div className="py-16 text-center text-slate-500 text-sm">
              Loading notification records...
            </div>
          ) : notifications.length === 0 ? (
            <div className="py-16 text-center text-slate-500 text-sm bg-slate-900/40 rounded-2xl border border-slate-800">
              No notifications to display.
            </div>
          ) : (
            <div className="space-y-2.5">
              {notifications.map((notif) => {
                const isUnread = !notif.read_at;

                return (
                  <div
                    key={notif.id}
                    className={`bg-slate-900/60 border rounded-2xl p-4 backdrop-blur flex items-start justify-between gap-4 transition ${
                      isUnread
                        ? 'border-blue-500/40 bg-blue-950/10'
                        : 'border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-start space-x-3">
                      <div className="mt-0.5">
                        {notif.severity === 'CRITICAL' || notif.severity === 'ERROR' ? (
                          <AlertOctagon className="w-4 h-4 text-rose-400" />
                        ) : notif.severity === 'WARNING' ? (
                          <AlertTriangle className="w-4 h-4 text-amber-400" />
                        ) : (
                          <Info className="w-4 h-4 text-blue-400" />
                        )}
                      </div>

                      <div className="space-y-1">
                        <div className="flex items-center space-x-2">
                          <span className="text-xs font-bold text-white">{notif.title}</span>
                          {isUnread && (
                            <span className="w-2 h-2 rounded-full bg-blue-500 inline-block"></span>
                          )}
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                            {notif.notification_type}
                          </span>
                        </div>
                        <p className="text-xs text-slate-300 leading-relaxed">{notif.message}</p>
                        <div className="flex items-center space-x-3 text-[10px] text-slate-500 font-mono pt-1">
                          <span>{new Date(notif.created_at).toLocaleString()}</span>
                          <span>Channel: {notif.delivery_channel}</span>
                          <span>Status: {notif.status}</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2 self-start shrink-0">
                      {isUnread && (
                        <button
                          onClick={() => handleMarkRead(notif.id)}
                          className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition cursor-pointer"
                          title="Mark as read"
                        >
                          <Check className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      ) : (
        /* Channel Preferences Tab */
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 backdrop-blur space-y-4">
          <div>
            <h2 className="text-base font-semibold text-white">Delivery Channel Configuration</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Control which types of notifications trigger in-app updates and emails.
            </p>
          </div>

          <div className="flex items-start gap-2.5 p-3.5 rounded-xl bg-slate-950/60 border border-amber-500/20 text-slate-300 text-xs">
            <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <span>
              <span className="font-semibold text-amber-300">Policy Note:</span> Critical system alerts
              and security incidents cannot be disabled to ensure compliance.
            </span>
          </div>

          <div className="divide-y divide-slate-800/60">
            {[
              { type: 'ALL', label: 'All General Notifications', desc: 'Global toggle for standard operational alerts' },
              { type: 'SURVEY_ASSIGNED', label: 'Survey Assignment', desc: 'Field survey commissioning and appointment alerts' },
              { type: 'VALIDATION_ALERT', label: 'Topology & GIS Validation', desc: 'Notices regarding spatial overlap, sliver or vertical clashes' },
              { type: 'CASE_ASSIGNMENT', label: 'Workflow Case Transitions', desc: 'Updates on citizen service requests and case status' },
              { type: 'SYSTEM_ALERT', label: 'System & Security Alerts', desc: 'Critical compliance and infrastructure alerts (Mandatory)', mandatory: true },
            ].map((item) => {
              const inAppPref = preferences.find(
                (p) => p.notification_type === item.type && p.channel === 'IN_APP'
              );
              const emailPref = preferences.find(
                (p) => p.notification_type === item.type && p.channel === 'EMAIL'
              );

              return (
                <div key={item.type} className="py-4 flex items-center justify-between">
                  <div>
                    <span className="text-xs font-semibold text-white block">{item.label}</span>
                    <span className="text-[11px] text-slate-400 block">{item.desc}</span>
                  </div>

                  <div className="flex items-center space-x-4">
                    {/* IN_APP toggle */}
                    <label className="flex items-center space-x-1.5 text-xs text-slate-300 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={item.mandatory ? true : inAppPref ? inAppPref.enabled : true}
                        disabled={item.mandatory}
                        onChange={() =>
                          handleTogglePreference(
                            item.type,
                            'IN_APP',
                            inAppPref ? inAppPref.enabled : true
                          )
                        }
                        className="rounded border-slate-700 bg-slate-950 text-blue-600 disabled:opacity-50"
                      />
                      <span>In-App</span>
                    </label>

                    {/* EMAIL toggle */}
                    <label className="flex items-center space-x-1.5 text-xs text-slate-300 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={item.mandatory ? true : emailPref ? emailPref.enabled : true}
                        disabled={item.mandatory}
                        onChange={() =>
                          handleTogglePreference(
                            item.type,
                            'EMAIL',
                            emailPref ? emailPref.enabled : true
                          )
                        }
                        className="rounded border-slate-700 bg-slate-950 text-blue-600 disabled:opacity-50"
                      />
                      <span>Email</span>
                    </label>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
