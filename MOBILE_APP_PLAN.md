# ACE Real Estate Mobile App Implementation Plan

## Overview

This document outlines the implementation plan for adding a mobile notification app to the ACE Real Estate system. The app will notify real estate agents when high-interest/compatibility leads are actively chatting.

## Current System Analysis

### Existing Infrastructure
- **Event System**: Robust event bus (`app/services/event_bus.py`) with publish/subscribe capability
- **Lead Scoring**: DeepSeek AI integration classifies leads with:
  - `interest`: "High" | "Medium" | "Low" 
  - `compatibility`: 0-100 score
  - `category`: "good_fit" | "could_fit" | "bad_fit"
- **Multi-tenant**: Each real estate agency is isolated by `tenant_slug`
- **Real-time Events**: SSE and long-polling already implemented

### Notification Triggers
High-interest leads are identified when:
- `interest` = "High" (compatibility >= 70)
- `category` = "good_fit" 
- `compatibility` >= 85 (for meeting-ready leads)

## Mobile App Architecture

### Technology Stack
- **Mobile Framework**: Ionic Angular (cross-platform iOS/Android/Web)
- **Push Notifications**: Firebase Cloud Messaging (FCM) + Capacitor Push Notifications
- **State Management**: Angular Services + RxJS (consistent with existing frontends)
- **Navigation**: Ionic Router (Angular Router)
- **Authentication**: JWT tokens (reuse existing backend auth services)

### App Structure
```
mobile-app/
├── src/
│   ├── app/
│   │   ├── pages/              # Ionic pages (screens)
│   │   │   ├── login/
│   │   │   ├── dashboard/
│   │   │   ├── notifications/
│   │   │   └── settings/
│   │   ├── components/         # Reusable components
│   │   ├── services/           # Angular services
│   │   │   ├── api.service.ts  # Backend API client
│   │   │   ├── auth.service.ts # Authentication
│   │   │   └── push.service.ts # Push notifications
│   │   ├── models/            # TypeScript interfaces
│   │   └── guards/            # Route guards
│   ├── assets/               # Images, fonts, etc.
│   ├── theme/               # Ionic theming
│   └── environments/        # Environment configs
├── android/                 # Android platform
├── ios/                    # iOS platform
├── capacitor.config.ts     # Capacitor configuration
└── package.json
```

## Backend Changes

### 1. Database Schema Extensions

**New Tables:**
```sql
-- Device registration for push notifications
CREATE TABLE device_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
    device_token TEXT NOT NULL,
    device_type VARCHAR(10) NOT NULL, -- 'ios' or 'android'
    app_version VARCHAR(20),
    device_info JSONB,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Notification preferences per user
CREATE TABLE notification_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    high_interest_leads BOOLEAN DEFAULT true,
    meeting_ready_leads BOOLEAN DEFAULT true,
    new_conversations BOOLEAN DEFAULT false,
    min_compatibility_score INTEGER DEFAULT 70,
    quiet_hours_start TIME,
    quiet_hours_end TIME,
    timezone VARCHAR(50) DEFAULT 'Europe/Ljubljana',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Notification history/delivery tracking
CREATE TABLE notification_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    device_token_id INTEGER REFERENCES device_tokens(id) ON DELETE CASCADE,
    lead_sid VARCHAR(64),
    notification_type VARCHAR(50) NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    payload JSONB,
    status VARCHAR(20) DEFAULT 'sent', -- 'sent', 'delivered', 'clicked', 'failed'
    sent_at TIMESTAMP DEFAULT NOW(),
    delivered_at TIMESTAMP,
    clicked_at TIMESTAMP
);
```

### 2. New API Endpoints

**Mobile API Router** (`app/api/mobile.py`):
```python
@router.post("/register-device")
def register_device(device_data: DeviceRegistration, user: User = Depends(get_current_user))

@router.delete("/unregister-device")
def unregister_device(device_token: str, user: User = Depends(get_current_user))

@router.get("/notifications/preferences")
def get_notification_preferences(user: User = Depends(get_current_user))

@router.patch("/notifications/preferences")
def update_notification_preferences(prefs: NotificationPreferences, user: User = Depends(get_current_user))

@router.get("/notifications/history")
def get_notification_history(user: User = Depends(get_current_user))

@router.post("/notifications/test")
def send_test_notification(user: User = Depends(get_current_user))
```

### 3. Push Notification Service

**New Service** (`app/services/push_notification_service.py`):
```python
class PushNotificationService:
    def __init__(self):
        # Initialize Firebase Admin SDK
        
    async def send_high_interest_notification(self, lead: Lead, tenant_slug: str):
        # Send to all active devices for tenant users
        
    async def send_to_user(self, user_id: int, notification: NotificationPayload):
        # Send notification to specific user's devices
        
    def create_high_interest_payload(self, lead: Lead) -> NotificationPayload:
        # Create notification payload for high-interest lead
```

### 4. Event Integration

**Enhanced Flow Service** (`app/services/flow_service.py`):
```python
# Add to _apply_ai_to_lead function
async def _apply_ai_to_lead(sid: str, result: dict | None):
    # ... existing code ...
    
    # NEW: Check for high-interest leads and send notifications
    if result and should_notify_high_interest(result):
        from app.services.push_notification_service import PushNotificationService
        push_service = PushNotificationService()
        await push_service.send_high_interest_notification(lead, tenant_slug)
        
        # Publish to event bus for real-time dashboard updates
        await event_bus.publish(sid, "lead.high_interest", {
            "lead_id": lead.id,
            "compatibility": result.get("compatibility"),
            "interest": result.get("interest")
        })

def should_notify_high_interest(ai_result: dict) -> bool:
    return (
        ai_result.get("interest") == "High" or
        ai_result.get("compatibility", 0) >= 85 or
        ai_result.get("category") == "good_fit"
    )
```

## Implementation Phases

### Phase 1: Backend Foundation (Week 1-2)
- [ ] Add database schema (device_tokens, notification_preferences, notification_history)
- [ ] Create mobile API endpoints
- [ ] Set up Firebase Cloud Messaging
- [ ] Implement PushNotificationService
- [ ] Add notification triggers to flow service
- [ ] Unit tests for notification logic

### Phase 2: Mobile App Core (Week 3-4)
- [ ] Initialize React Native project with TypeScript
- [ ] Set up navigation structure
- [ ] Implement authentication screen (JWT login)
- [ ] Create dashboard with lead summary
- [ ] Set up FCM integration
- [ ] Device registration flow

### Phase 3: Notification Features (Week 5-6)
- [ ] Push notification handling (foreground/background)
- [ ] Notification preferences screen
- [ ] Test notification functionality
- [ ] Notification history view
- [ ] Deep linking to lead details

### Phase 4: Enhanced Features (Week 7-8)
- [ ] Real-time dashboard updates via WebSocket/SSE
- [ ] Lead detail view with quick actions
- [ ] Quiet hours and timezone support
- [ ] Notification analytics
- [ ] App icon badges for unread notifications

### Phase 5: Testing & Deployment (Week 9-10)
- [ ] End-to-end testing
- [ ] iOS App Store submission
- [ ] Google Play Store submission
- [ ] Backend deployment with Firebase setup
- [ ] User documentation

## Notification Flow Diagram

```
[Lead Chatting] 
      ↓
[AI Classification via DeepSeek]
      ↓
[High Interest Detected] 
    (interest="High" OR compatibility>=85)
      ↓
[Push Notification Service]
      ↓
[Check User Preferences]
   (tenant users, quiet hours, etc.)
      ↓
[Send FCM Push Notification]
      ↓
[Mobile App Receives Notification]
      ↓
[User Can View Lead Details]
```

## Security Considerations

### Device Token Management
- Rotate device tokens on app updates
- Clean up inactive device tokens (30+ days)
- Encrypt sensitive notification payloads

### Authentication
- Reuse existing JWT authentication
- Implement refresh token mechanism for mobile
- Rate limit API endpoints

### Privacy
- Only send minimal lead info in push notifications
- Full details fetched after user authentication
- Respect tenant data isolation

## Configuration

### Environment Variables
```bash
# Firebase Configuration
FIREBASE_PROJECT_ID=ace-real-estate-prod
FIREBASE_PRIVATE_KEY_PATH=/secrets/firebase-admin-key.json
FIREBASE_DATABASE_URL=https://ace-real-estate-prod.firebaseio.com

# Mobile App Settings  
MOBILE_API_VERSION=v1
NOTIFICATION_RATE_LIMIT=100  # per user per hour
NOTIFICATION_RETENTION_DAYS=90
```

### Firebase Setup
1. Create Firebase project
2. Enable Cloud Messaging
3. Generate service account key
4. Configure FCM for iOS/Android apps

## Success Metrics

### Technical Metrics
- Notification delivery rate (target: >95%)
- App crash rate (target: <0.1%)
- API response time (target: <500ms)
- Push notification latency (target: <30 seconds)

### Business Metrics  
- User engagement with notifications (target: >60% open rate)
- Lead response time improvement (target: 50% faster)
- Agent satisfaction with mobile alerts

## Maintenance Plan

### Regular Tasks
- Monitor notification delivery rates
- Clean up old device tokens and notification history
- Update mobile app dependencies
- Review and optimize notification triggers

### Scaling Considerations
- Implement notification batching for high-volume tenants
- Add push notification queuing/retry logic
- Consider notification templates for customization
- Plan for multi-language support

## Development Tools

### Required Tools
- **Backend**: Python 3.x, FastAPI, PostgreSQL, Firebase Admin SDK
- **Mobile**: Node.js, React Native CLI, Android Studio, Xcode
- **Testing**: Pytest, Detox (E2E), Firebase Test Lab
- **Monitoring**: Firebase Analytics, Sentry for error tracking

### Development Environment Setup
1. Install React Native development environment
2. Set up Firebase project and download config files
3. Configure development certificates for iOS
4. Set up Android development environment
5. Install required VS Code extensions for React Native

This comprehensive plan provides a structured approach to implementing mobile notifications while leveraging the existing ACE Real Estate architecture and ensuring scalability for the multi-tenant system.