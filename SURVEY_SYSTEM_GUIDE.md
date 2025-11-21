# ACE Survey System - Complete Implementation Guide

## Overview

The ACE Real Estate system has been transformed from a conversational AI chatbot to a **structured survey system** while preserving the critical **agent takeover** functionality. Users now fill out predefined forms created in a visual flow designer instead of having open-ended AI conversations.

---

## 🎯 Key Changes

### Before (Chatbot System)
- Guest had open-ended conversations with AI
- DeepSeek AI qualified leads through chat
- Unstructured responses
- Flow was AI-guided

### After (Survey System)
- Guest fills structured survey forms
- Questions predefined in flow designer
- Structured, validated responses
- Flow is designer-controlled
- **Agent takeover still works** - agents can jump in anytime

---

## 📁 File Changes

### Backend

#### New/Modified Files:

1. **`app/models/orm.py`** - Added survey fields to Lead model:
   - `survey_started_at` - When survey was started
   - `survey_completed_at` - When completed
   - `survey_answers` - JSON dict of {node_id: answer}
   - `survey_progress` - 0-100 percentage

2. **`app/models/lead.py`** - Pydantic Lead model updated with survey fields

3. **`app/models/chat.py`** - Added `SurveySubmitRequest` model

4. **`app/services/lead_service.py`** - New functions:
   - `start_survey(sid)` - Mark survey as started
   - `update_survey_answer(sid, node_id, answer)` - Store individual answer
   - `update_survey_progress(sid, progress, answers)` - Update completion %
   - `get_survey_answers(sid)` - Retrieve answers

5. **`app/api/chat.py`** - New endpoint:
   - `POST /survey/submit` - Submit survey answer with progress tracking
   - Checks for agent takeover (pauses survey if active)
   - Publishes SSE events: `survey.progress`, `survey.completed`, `survey.paused`

### Frontend - ACE-Chatbot

6. **`frontend/ACE-Chatbot/src/app/survey-form.component.ts`** - NEW
   - Complete survey form component with stepper UI
   - Renders questions as form fields (not chat bubbles)
   - Progress bar, back/next navigation
   - Supports: choices, text input, email, phone, dual-contact
   - Submits answers in real-time to backend

7. **`frontend/ACE-Chatbot/src/app/app.component.ts`** - Modified:
   - Added `appMode: 'survey' | 'chat'` - Mode switcher
   - Added `surveyFlow` - Loaded from backend
   - Added `loadSurveyFlow()` - Fetches conversation flow
   - Added `onSurveyCompleted()`, `onSurveyPaused()` - Event handlers
   - Listen to SSE `survey.paused` event → switches to chat mode

8. **`frontend/ACE-Chatbot/src/app/app.component.html`** - Modified:
   - Conditional rendering: `*ngIf="appMode === 'survey'"` / `*ngIf="appMode === 'chat'"`
   - Shows survey form by default, chat interface on takeover

### Frontend - Manager Dashboard

9. **`frontend/manager-dashboard/src/app/survey-answers/survey-answers.component.ts`** - NEW
   - Display structured survey answers
   - Progress bar and completion status
   - Formatted question/answer pairs
   - Timestamps (started/completed)

### Scripts

10. **`scripts/migrate_survey_fields.py`** - NEW
    - Database migration script
    - Adds survey columns to existing database
    - Safe to run multiple times

---

## 🚀 Setup Instructions

### 1. Database Migration

Run the migration script to add survey fields:

```bash
cd /home/maksich/Documents/ACE-RealEstate
python3 scripts/migrate_survey_fields.py
```

Or if using venv:

```bash
./run_backend.sh  # This will create venv if needed
source venv/bin/activate
python scripts/migrate_survey_fields.py
```

### 2. Backend Startup

```bash
./run_backend.sh
```

The backend will:
- Start on `http://localhost:8000`
- Load conversation flow from `data/conversation_flow.json`
- Expose `/survey/submit` endpoint

### 3. Frontend Startup

#### ACE-Chatbot (Customer-facing survey)

```bash
cd frontend/ACE-Chatbot
npm install
ng serve  # Runs on http://localhost:4200
```

#### Manager Dashboard (Lead management)

```bash
cd frontend/manager-dashboard
npm install
ng serve --port 4400
```

---

## 🎨 How It Works

### Survey Flow

1. **User visits chatbot** → `appMode = 'survey'`
2. **Frontend loads flow** from `GET /api/instances/default/conversation_flow`
3. **SurveyFormComponent renders** first question
4. **User answers** → `POST /survey/submit` with:
   ```json
   {
     "sid": "abc123",
     "node_id": "intent",
     "answer": "Kupujem",
     "progress": 14,
     "all_answers": {"intent": "Kupujem"}
   }
   ```
5. **Backend stores** answer in `lead.survey_answers`
6. **Progress updates** in real-time
7. **On completion** (progress = 100%):
   - `lead.survey_completed_at` is set
   - `lead.stage` updated to "Qualified"
   - `lead.score` bumped to 60+

### Agent Takeover Flow

1. **Agent clicks "Claim"** in manager dashboard
2. **Backend** calls `takeover.enable(sid)`
3. **SSE event** `survey.paused` sent to frontend
4. **Frontend** detects event → calls `onSurveyPaused()`
5. **Mode switches** `appMode = 'chat'`, `humanMode = true`
6. **Chat interface** replaces survey form
7. **Agent messages** appear with `role = 'staff'`
8. **Bot stops responding** while takeover is active

---

## 📊 Survey Data Structure

### In Database (Lead table)

```python
lead.survey_answers = {
    "welcome": {"email": "user@example.com", "phone": "+386 123 456"},
    "intent": "Kupujem",
    "property_type": "Stanovanje",
    "location": "Ljubljana in okolica",
    "budget": "200k – 400k €",
    "timing": "Zelo kmalu (1–2 tedna)",
    "financing": "Hipoteka / kredit",
    "history": "Ne",
    "notes": "Želim balkon in parkiranje"
}

lead.survey_progress = 100
lead.survey_started_at = "2025-11-21T15:00:00Z"
lead.survey_completed_at = "2025-11-21T15:05:23Z"
```

### API Response

```json
{
  "ok": true,
  "completed": true,
  "progress": 100,
  "message": "Hvala za sodelovanje! Kmalu se oglasimo.",
  "lead": {
    "stage": "Qualified",
    "score": 65,
    "progress": 100
  }
}
```

---

## 🔧 Customization

### Adding New Question Types

In `survey-form.component.ts`, extend the `inputType` handling:

```typescript
// Current types: 'single', 'dual-contact', 'email', 'phone'
// Add new type in template:
<div *ngIf="currentNode.inputType === 'date'">
  <input type="date" [(ngModel)]="dateAnswer" class="form-input">
</div>
```

### Modifying Flow

Use the **Flow Designer** in manager dashboard:
1. Go to `http://localhost:4400`
2. Click "Flow" tab
3. Edit nodes visually
4. Export JSON
5. Update `data/conversation_flow.json`

### Custom Question Labels

Edit `SurveyAnswersComponent.formatQuestionId()`:

```typescript
const labels: Record<string, string> = {
  'welcome': 'Kontakt',
  'my_custom_node': 'Moje vprašanje',
  // Add more mappings...
};
```

---

## 🧪 Testing

### Manual Testing

1. **Survey Flow**:
   ```bash
   # Terminal 1: Backend
   ./run_backend.sh
   
   # Terminal 2: Frontend
   cd frontend/ACE-Chatbot && ng serve
   
   # Browser: http://localhost:4200
   # Fill out survey, check progress bar, submit
   ```

2. **Agent Takeover**:
   ```bash
   # Terminal 3: Manager Dashboard
   cd frontend/manager-dashboard && ng serve --port 4400
   
   # Browser: http://localhost:4400
   # Find lead, click "Claim", send message
   # Check customer UI switches to chat mode
   ```

3. **Survey Data Display**:
   - Manager dashboard → Click on lead
   - Should see survey answers formatted nicely
   - Progress bar shows completion percentage

### API Testing

```bash
# Test survey submission
curl -X POST http://localhost:8000/survey/submit \
  -H "Content-Type: application/json" \
  -d '{
    "sid": "test123",
    "node_id": "intent",
    "answer": "Kupujem",
    "progress": 14,
    "all_answers": {"intent": "Kupujem"}
  }'

# Expected response:
# {"ok": true, "completed": false, "progress": 14, "answers_count": 1}
```

---

## 🎯 Key Features Preserved

✅ **Agent Takeover** - Works seamlessly with surveys  
✅ **Flow Designer** - Visual editor still functional  
✅ **Real-time Events** - SSE for live updates  
✅ **Multi-tenant** - Tenant isolation maintained  
✅ **Lead Scoring** - Auto-qualification on completion  

---

## 🐛 Troubleshooting

### Survey Not Loading

**Issue**: Survey form doesn't appear, falls back to chat mode

**Fix**: Check flow endpoint
```bash
curl http://localhost:8000/api/instances/default/conversation_flow
# Should return JSON with "nodes" array
```

### Answers Not Saving

**Issue**: Survey submits but answers don't appear in dashboard

**Fix**: 
1. Check backend logs for errors
2. Verify migration ran: `python scripts/migrate_survey_fields.py`
3. Check database:
   ```bash
   sqlite3 ace_dev.db "PRAGMA table_info(leads);"
   # Should show survey_* columns
   ```

### Takeover Not Working

**Issue**: Agent claims session but survey doesn't pause

**Fix**:
1. Check SSE connection in browser DevTools → Network → `stream`
2. Verify `survey.paused` event is published
3. Check `onSurveyPaused()` is called in frontend logs

---

## 📈 Future Enhancements

Completed features:
- ✅ Survey form component
- ✅ Progress tracking
- ✅ Agent takeover integration
- ✅ Answer storage and display
- ✅ Database schema

Potential additions:
- ⚪ Conditional branching logic (advanced flows)
- ⚪ Multi-page surveys (step navigation)
- ⚪ File upload questions
- ⚪ Survey analytics dashboard
- ⚪ A/B testing different flows
- ⚪ Survey templates library
- ⚪ Validation rules editor in flow designer

---

## 📚 Additional Resources

- **Flow Designer Guide**: See flow-designer component for visual editing
- **API Documentation**: Check `app/api/chat.py` for all endpoints
- **Database Schema**: See `app/models/orm.py` for complete models
- **Lead Service**: See `app/services/lead_service.py` for business logic

---

## 🙋 Need Help?

1. Check backend logs: `./run_backend.sh` output
2. Check browser console: DevTools → Console
3. Check network requests: DevTools → Network tab
4. Review this guide's troubleshooting section

---

**Last Updated**: 2025-11-21  
**Version**: 1.0.0  
**Status**: ✅ Production Ready
