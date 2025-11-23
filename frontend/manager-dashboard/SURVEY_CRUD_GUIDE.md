# Survey CRUD Implementation Guide

## Overview

Complete implementation of survey management functionality in the Manager Dashboard, allowing users to create, edit, delete, and publish surveys with customizable flows.

## Features Implemented

### 1. Survey List View (`/surveys`)
- **Location**: `survey-list.component.ts`
- **Features**:
  - View all surveys for your organization
  - Display survey name, type (regular/A-B test), status (draft/live/archived)
  - Show public URL for each survey
  - Quick actions: Edit Flow, Publish, Archive, Delete
  - Create new survey button

### 2. Survey Form (`/surveys/new` and `/surveys/:id/metadata`)
- **Location**: `survey-form.component.ts`
- **Features**:
  - Create new survey with metadata:
    - Survey name (internal use)
    - URL slug (for public access)
    - Type: Regular or A/B Test
  - Auto-generate slug from name
  - Show public URL preview
  - Validate inputs before saving
  - Navigate directly to flow builder after creation

### 3. Survey Flow Builder (`/surveys/:id/edit`)
- **Location**: `simple-survey-builder.component.ts`
- **Features**:
  - Visual drag-and-drop question editor
  - Support for multiple question types:
    - Multiple choice (with scoring)
    - Text input
    - Email
    - Phone
    - Contact (email + phone)
  - Save flow to specific survey
  - Load existing flow
  - Preview mode
  - Back to surveys button
  - Survey name and status display

## Routes

```typescript
/surveys                    → Survey List
/surveys/new               → Create New Survey Form
/surveys/:id/edit          → Flow Builder for Survey
/surveys/:id/metadata      → Edit Survey Metadata
```

## Navigation Flow

```
Dashboard "FLOW" Tab
    ↓
    "Open Survey Manager" button
    ↓
Survey List (/surveys)
    ↓
    "Create Survey" button
    ↓
Survey Form (/surveys/new)
    ↓
    Fill name, slug, type
    ↓
    "Create & Build Flow" button
    ↓
Flow Builder (/surveys/:id/edit)
    ↓
    Add questions, configure
    ↓
    "Save Flow" button
    ↓
Back to Survey List
    ↓
    "Publish" button → Makes survey live
```

## Public Survey URLs

After creating a survey with slug `my-survey`:
- **Public URL**: `http://yourdomain.com/s/my-survey`
- **A/B Test Variant A**: `http://yourdomain.com/s/my-survey/a`
- **A/B Test Variant B**: `http://yourdomain.com/s/my-survey/b`

## API Integration

### Backend Endpoints Used

```
GET    /api/organizations/{org_id}/surveys          → List surveys
POST   /api/organizations/{org_id}/surveys          → Create survey
GET    /api/organizations/{org_id}/surveys/{id}     → Get survey
PUT    /api/organizations/{org_id}/surveys/{id}     → Update survey
DELETE /api/organizations/{org_id}/surveys/{id}     → Delete survey
POST   /api/organizations/{org_id}/surveys/{id}/publish  → Publish
POST   /api/organizations/{org_id}/surveys/{id}/archive  → Archive
```

### Survey Model

```typescript
interface Survey {
  id: number;
  organization_id: number;
  name: string;
  slug: string;
  survey_type: 'regular' | 'ab_test';
  status: 'draft' | 'live' | 'archived';
  flow_json?: any;               // Regular survey flow
  variant_a_flow?: any;          // A/B test variant A
  variant_b_flow?: any;          // A/B test variant B
  created_at: string;
  updated_at: string;
  published_at?: string;
}
```

## Usage

### Creating a Survey

1. Navigate to Dashboard and click "FLOW" tab
2. Click "Open Survey Manager"
3. Click "+ Create Survey"
4. Fill in:
   - **Survey Name**: "Customer Satisfaction Survey"
   - **URL Slug**: Auto-generated as `customer-satisfaction-survey`
   - **Survey Type**: Regular or A/B Test
5. Click "Create & Build Flow"
6. Add questions using the builder
7. Click "Save Flow"
8. Go back to list and click "Publish"

### Editing a Survey Flow

1. Go to Survey List
2. Click survey name or "Edit Flow" button
3. Modify questions
4. Click "Save Flow"

### Deleting a Survey

1. Go to Survey List
2. Click "Delete" button
3. Confirm deletion (cannot be undone)

## Components Created/Modified

### New Components
- `survey-form.component.ts` - Survey metadata form
- Modified `survey-list.component.ts` - Enhanced with CRUD operations
- Modified `simple-survey-builder.component.ts` - Now works with specific surveys

### Updated Files
- `app.routes.ts` - Added survey routes
- `app.component.html` - Updated Flow tab
- `app.component.ts` - Added navigation method
- `surveys.service.ts` - Already had all methods (no changes needed)

## Status Badges

- **draft** - Orange badge, survey being edited
- **live** - Green badge, survey published and accepting responses
- **archived** - Gray badge, survey no longer active

## Next Steps (Future Enhancements)

1. **Statistics Page**: View response analytics per survey
2. **A/B Test Builder**: Separate tabs for variant A and B flows
3. **Survey Duplication**: Clone existing surveys
4. **Response Filtering**: Filter responses by survey
5. **Export**: Download survey responses as CSV
6. **Survey Templates**: Pre-built survey templates
7. **Conditional Logic**: Show questions based on previous answers

## Troubleshooting

### Survey Not Saving
- Check console for API errors
- Verify backend is running
- Check JWT token is valid
- Ensure flow_json is valid JSON

### Can't Delete Survey
- Check if survey has responses (may need backend protection)
- Verify user has permission to delete

### Public URL Not Working
- Ensure survey is published (status: live)
- Verify slug is unique
- Check backend public_survey.py routes

## Testing Checklist

- [ ] Create new survey
- [ ] Edit survey name/slug
- [ ] Add questions to flow
- [ ] Save flow successfully
- [ ] Publish survey
- [ ] Archive survey
- [ ] Delete survey
- [ ] Navigate between all routes
- [ ] View public survey URL

## Code Style

- Standalone Angular components
- TypeScript strict mode
- Reactive programming with RxJS
- Clean separation of concerns
- Inline templates and styles for simplicity
