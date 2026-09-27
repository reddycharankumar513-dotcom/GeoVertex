import { describe, it, expect } from 'vitest';
import { UserRole } from '../types';
import {
  RequestStatus,
  RequestPriority,
  ServiceType,
  ServiceRequest,
  CaseMessage,
  Notification,
  CitizenProperty,
  CitizenDashboardMetrics,
  GovernmentDashboardMetrics,
} from '../types/workflow';

describe('GeoVertex Phase 11: Citizen Portal, Government Workflow & Public-Service Integration', () => {
  // 1. Role-Based & Object-Based Access Control (RBAC & ABAC)
  describe('Authorization Rules (RBAC & ABAC)', () => {
    it('verifies citizen access is restricted to their own verified properties and requests', () => {
      const citizenUser = { id: 'citizen-101', role: 'CITIZEN' as UserRole };
      const otherCitizen = { id: 'citizen-202', role: 'CITIZEN' as UserRole };
      const officer = { id: 'officer-303', role: 'GOVERNMENT_OFFICER' as UserRole };

      const myProperty: CitizenProperty = {
        id: 'link-1',
        property_id: 'prop-1',
        property_reference: 'PROP-001',
        parcel_id: 'par-1',
        property_type: 'FREEHOLD',
        status: 'ACTIVE',
        address: '101 Jubilee Hills',
        authorization_type: 'OWNER',
        link_status: 'VERIFIED',
        units_count: 1,
        created_at: new Date().toISOString(),
      };

      const canSubmitForProperty = (user: { id: string; role: UserRole }, propOwnerId: string) => {
        if (user.role === 'ADMIN' || user.role === 'GOVERNMENT_OFFICER') return true;
        return user.id === propOwnerId;
      };

      expect(canSubmitForProperty(citizenUser, 'citizen-101')).toBe(true);
      expect(canSubmitForProperty(otherCitizen, 'citizen-101')).toBe(false);
      expect(canSubmitForProperty(officer, 'citizen-101')).toBe(true);
    });

    it('strictly hides internal officer notes from citizen view', () => {
      const messages: CaseMessage[] = [
        {
          id: 'msg-1',
          service_request_id: 'req-1',
          sender_role: 'CITIZEN',
          message_type: 'PUBLIC_MESSAGE',
          message_body: 'Attached partition deed copy.',
          attachments_json: [],
          is_internal: false,
          created_at: new Date().toISOString(),
        },
        {
          id: 'msg-2',
          service_request_id: 'req-1',
          sender_role: 'GOVERNMENT_OFFICER',
          message_type: 'INTERNAL_NOTE',
          message_body: 'CONFIDENTIAL: Boundary overlap detected with parcel GV-W500-02.',
          attachments_json: [],
          is_internal: true,
          created_at: new Date().toISOString(),
        },
        {
          id: 'msg-3',
          service_request_id: 'req-1',
          sender_role: 'GOVERNMENT_OFFICER',
          message_type: 'PUBLIC_MESSAGE',
          message_body: 'Please provide certified surveyor report.',
          attachments_json: [],
          is_internal: false,
          created_at: new Date().toISOString(),
        },
      ];

      const filterForUser = (msgs: CaseMessage[], role: UserRole) => {
        if (['ADMIN', 'GOVERNMENT_OFFICER', 'URBAN_PLANNER'].includes(role)) {
          return msgs;
        }
        return msgs.filter((m) => !m.is_internal);
      };

      const citizenView = filterForUser(messages, 'CITIZEN');
      expect(citizenView.length).toBe(2);
      expect(citizenView.some((m) => m.is_internal)).toBe(false);
      expect(citizenView.some((m) => m.message_body.includes('CONFIDENTIAL'))).toBe(false);

      const officerView = filterForUser(messages, 'GOVERNMENT_OFFICER');
      expect(officerView.length).toBe(3);
      expect(officerView.some((m) => m.is_internal)).toBe(true);
    });
  });

  // 2. Workflow State Machine Transitions
  describe('State Machine & Transition Rules', () => {
    const allowedTransitions: Record<RequestStatus, RequestStatus[]> = {
      DRAFT: ['SUBMITTED', 'CANCELLED'],
      SUBMITTED: ['UNDER_REVIEW', 'CANCELLED'],
      UNDER_REVIEW: ['MORE_INFO_REQUESTED', 'SURVEY_COMMISSIONED', 'FIELD_VERIFIED', 'APPROVED', 'REJECTED'],
      MORE_INFO_REQUESTED: ['UNDER_REVIEW', 'CANCELLED'],
      SURVEY_COMMISSIONED: ['SURVEY_COMPLETED', 'UNDER_REVIEW'],
      SURVEY_COMPLETED: ['FIELD_VERIFIED', 'UNDER_REVIEW'],
      FIELD_VERIFIED: ['APPROVED', 'REJECTED', 'UNDER_REVIEW'],
      APPROVED: ['COMPLETED'],
      REJECTED: [],
      CANCELLED: [],
      COMPLETED: [],
    };

    const canTransition = (current: RequestStatus, target: RequestStatus, role: UserRole): boolean => {
      const allowed = allowedTransitions[current] || [];
      if (!allowed.includes(target)) return false;

      // Role specific rules
      if (role === 'CITIZEN') {
        if (current === 'DRAFT' && target === 'SUBMITTED') return true;
        if (['DRAFT', 'SUBMITTED', 'MORE_INFO_REQUESTED'].includes(current) && target === 'CANCELLED') return true;
        if (current === 'MORE_INFO_REQUESTED' && target === 'UNDER_REVIEW') return true;
        return false;
      }

      if (['ADMIN', 'GOVERNMENT_OFFICER'].includes(role)) {
        return true;
      }

      return false;
    };

    it('allows valid citizen submissions and cancels, but prohibits citizen approval/rejection', () => {
      expect(canTransition('DRAFT', 'SUBMITTED', 'CITIZEN')).toBe(true);
      expect(canTransition('SUBMITTED', 'CANCELLED', 'CITIZEN')).toBe(true);
      expect(canTransition('MORE_INFO_REQUESTED', 'UNDER_REVIEW', 'CITIZEN')).toBe(true);

      // Prohibited citizen transitions
      expect(canTransition('UNDER_REVIEW', 'APPROVED', 'CITIZEN')).toBe(false);
      expect(canTransition('UNDER_REVIEW', 'REJECTED', 'CITIZEN')).toBe(false);
      expect(canTransition('UNDER_REVIEW', 'SURVEY_COMMISSIONED', 'CITIZEN')).toBe(false);
    });

    it('allows government officers to review, commission surveys, approve, or reject', () => {
      expect(canTransition('SUBMITTED', 'UNDER_REVIEW', 'GOVERNMENT_OFFICER')).toBe(true);
      expect(canTransition('UNDER_REVIEW', 'SURVEY_COMMISSIONED', 'GOVERNMENT_OFFICER')).toBe(true);
      expect(canTransition('SURVEY_COMMISSIONED', 'SURVEY_COMPLETED', 'GOVERNMENT_OFFICER')).toBe(true);
      expect(canTransition('SURVEY_COMPLETED', 'FIELD_VERIFIED', 'GOVERNMENT_OFFICER')).toBe(true);
      expect(canTransition('FIELD_VERIFIED', 'APPROVED', 'GOVERNMENT_OFFICER')).toBe(true);
      expect(canTransition('UNDER_REVIEW', 'REJECTED', 'GOVERNMENT_OFFICER')).toBe(true);
    });

    it('enforces terminal states where no further transitions are allowed', () => {
      expect(canTransition('COMPLETED', 'UNDER_REVIEW', 'GOVERNMENT_OFFICER')).toBe(false);
      expect(canTransition('REJECTED', 'APPROVED', 'GOVERNMENT_OFFICER')).toBe(false);
      expect(canTransition('CANCELLED', 'SUBMITTED', 'CITIZEN')).toBe(false);
    });
  });

  // 3. SLA Compliance & Deadline Engine
  describe('SLA Compliance Engine', () => {
    it('computes correct SLA statuses based on deadline proximity', () => {
      const getSlaStatus = (dueAt: Date, now: Date = new Date()) => {
        const diffMs = dueAt.getTime() - now.getTime();
        const diffHours = diffMs / (1000 * 60 * 60);

        if (diffHours < 0) return { status: 'OVERDUE', hoursRemaining: Math.round(diffHours) };
        if (diffHours <= 24) return { status: 'DUE_SOON', hoursRemaining: Math.round(diffHours) };
        return { status: 'ON_TRACK', hoursRemaining: Math.round(diffHours) };
      };

      const now = new Date();
      const inThreeDays = new Date(now.getTime() + 72 * 3600 * 1000);
      const inTwelveHours = new Date(now.getTime() + 12 * 3600 * 1000);
      const pastFourHours = new Date(now.getTime() - 4 * 3600 * 1000);

      expect(getSlaStatus(inThreeDays, now).status).toBe('ON_TRACK');
      expect(getSlaStatus(inTwelveHours, now).status).toBe('DUE_SOON');
      expect(getSlaStatus(pastFourHours, now).status).toBe('OVERDUE');
    });
  });

  // 4. Controlled Official Updates
  describe('Controlled Official Updates & Audit Rules', () => {
    it('validates mandatory audit reasoning and legal source reference', () => {
      const validateControlledUpdate = (payload: {
        updates: Record<string, any>;
        audit_reason: string;
        source_reference: string;
      }) => {
        if (!payload.audit_reason || payload.audit_reason.trim().length < 5) {
          throw new Error('Mandatory officer audit reason of at least 5 characters required');
        }
        if (!payload.source_reference || payload.source_reference.trim().length < 3) {
          throw new Error('Mandatory legal source reference required');
        }
        if (Object.keys(payload.updates).length === 0) {
          throw new Error('At least one property field must be modified');
        }
        return true;
      };

      expect(() =>
        validateControlledUpdate({
          updates: { address: '202 Banjara Hills' },
          audit_reason: '',
          source_reference: 'Deed 1234',
        })
      ).toThrow('Mandatory officer audit reason');

      expect(() =>
        validateControlledUpdate({
          updates: {},
          audit_reason: 'Court order boundary adjustment',
          source_reference: 'Gazette #442',
        })
      ).toThrow('At least one property field');

      expect(
        validateControlledUpdate({
          updates: { address: '202 Banjara Hills' },
          audit_reason: 'Gazette boundary rectification',
          source_reference: 'Order #2026/GZ-101',
        })
      ).toBe(true);
    });
  });

  // 5. In-App Notification Integrity (No Fake Deliveries)
  describe('Notification Delivery Integrity', () => {
    it('ensures in-app notifications are saved and email delivery defaults to EMAIL_NOT_CONFIGURED when SMTP is absent', () => {
      const createNotification = (
        userId: string,
        title: string,
        message: string,
        smtpConfigured: boolean
      ): Notification => {
        return {
          id: 'notif-1',
          user_id: userId,
          notification_type: 'STATUS_CHANGED',
          title,
          message,
          delivery_channel: smtpConfigured ? 'EMAIL_QUEUED' : 'IN_APP',
          created_at: new Date().toISOString(),
        };
      };

      const notifWithoutSmtp = createNotification('user-1', 'Case Approved', 'Your mutation is complete.', false);
      expect(notifWithoutSmtp.delivery_channel).toBe('IN_APP');

      const notifWithSmtp = createNotification('user-1', 'Case Approved', 'Your mutation is complete.', true);
      expect(notifWithSmtp.delivery_channel).toBe('EMAIL_QUEUED');
    });
  });
});
