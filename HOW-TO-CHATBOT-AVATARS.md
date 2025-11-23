# HOW-TO: Chatbot Organization Avatars

This guide explains how the ACE-Chatbot displays organization-specific avatars dynamically.

## Overview

The chatbot automatically detects which organization it's serving and displays that organization's admin avatar. When a manager uploads their profile picture in the manager dashboard, it will automatically appear in their organization's chatbot.

## How Organization Detection Works

The chatbot tries multiple methods to detect the organization (in order of priority):

### Method 1: URL Path (Recommended for Production)
```
https://yourdomain.com/organizations/acme-realty/chatbot
```
Organization detected: `acme-realty`

### Method 2: Subdomain
```
https://acme-realty.yourdomain.com
```
Organization detected: `acme-realty`

### Method 3: Query Parameter
```
https://yourdomain.com/chatbot?org=acme-realty
```
Organization detected: `acme-realty`

### Method 4: LocalStorage (Development/Fallback)
```javascript
localStorage.setItem('ace_organization_slug', 'acme-realty');
```

## Testing Locally

### Option A: Using Query Parameter
1. Start the chatbot: `cd frontend/ACE-Chatbot && ng serve`
2. Visit: `http://localhost:4200?org=test-org`

### Option B: Using LocalStorage
1. Open browser console at `http://localhost:4200`
2. Run: `localStorage.setItem('ace_organization_slug', 'test-org')`
3. Refresh the page

### Option C: Using the Helper Script
1. Open `frontend/ACE-Chatbot/set-org-for-testing.js`
2. Copy the contents
3. Paste in browser console at `http://localhost:4200`
4. Refresh the page

## Backend Endpoint

The chatbot calls this public endpoint:

```
GET /api/organizations/{org_slug}/avatar

Response:
{
  "avatar_url": "/static/avatars/abc123.png",
  "organization_name": "ACME Real Estate"
}
```

**Security Note:** This endpoint is public (no authentication required) so chatbots can display the agent photo. It only returns the avatar URL, not sensitive user data.

## Deployment Configuration

### Single-Tenant Deployment
If you have one organization per domain, you can:
1. Set the organization slug in the chatbot environment config
2. Or use subdomain detection (e.g., `yourdomain.com` for single tenant)

### Multi-Tenant Deployment
Use one of these approaches:

**Option 1: Path-based** (Recommended)
```
yourdomain.com/organizations/acme-realty/chatbot
yourdomain.com/organizations/johnson-homes/chatbot
```

**Option 2: Subdomain-based**
```
acme-realty.yourdomain.com
johnson-homes.yourdomain.com
```

**Option 3: Query parameter-based**
```
yourdomain.com/chatbot?org=acme-realty
yourdomain.com/chatbot?org=johnson-homes
```

## Customization

### Change Default Avatar
Edit `/frontend/ACE-Chatbot/public/agents/default.png` to set the fallback avatar when:
- No organization is detected
- Organization has no admin with avatar
- API request fails

### Change Agent Name Display
The chatbot will automatically use the organization name as the agent name. To customize this:

Edit `app.component.ts`:
```typescript
if (response.organization_name) {
  this.agentName = `${response.organization_name} Team`; // Customize format
}
```

## Troubleshooting

### Avatar Not Loading

1. **Check browser console** for detection logs:
   ```
   [ACE] Organization detected from path: acme-realty
   [ACE] Loading avatar for organization: acme-realty
   [ACE] Agent photo URL set to: http://localhost:8000/static/avatars/...
   ```

2. **Verify organization exists**:
   ```bash
   curl http://localhost:8000/api/organizations/test-org/avatar
   ```

3. **Check admin has uploaded avatar**:
   - Login to manager dashboard
   - Click avatar → "Change Avatar"
   - Upload an image

4. **Verify CORS settings** if frontend/backend are on different domains

### Organization Not Detected

1. Check URL format matches one of the detection methods
2. Open browser console and look for detection logs
3. Manually set via localStorage for testing:
   ```javascript
   localStorage.setItem('ace_organization_slug', 'your-org-slug');
   location.reload();
   ```

### Avatar Shows But Is Broken

1. Check `static/avatars/` directory exists and is readable
2. Verify `app.mount("/static", ...)` is in `main.py`
3. Check avatar file exists at the returned path
4. Verify backend URL is correct in chatbot config

## Integration with Manager Dashboard

When a manager uploads their avatar:
1. **Manager Dashboard** calls `POST /api/users/me/avatar`
2. Avatar is saved to `static/avatars/{uuid}.{ext}`
3. User's `avatar_url` is updated in database
4. **Chatbot** calls `GET /api/organizations/{slug}/avatar`
5. Backend returns the first active admin's avatar
6. Chatbot displays the avatar automatically

**The synchronization is automatic** - no manual steps needed!

## Production Checklist

- [ ] Choose deployment model (path/subdomain/query)
- [ ] Update chatbot frontend with production backend URL
- [ ] Ensure `static/avatars/` is backed up
- [ ] Configure CORS for your domains
- [ ] Test avatar display with real organization slugs
- [ ] Add default avatar image to `/public/agents/default.png`
- [ ] Document organization slug format for clients
