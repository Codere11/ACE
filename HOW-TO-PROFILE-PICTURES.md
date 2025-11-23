# HOW-TO: Profile Picture Upload

This guide explains how managers can upload and change their profile pictures in the ACE Real Estate Manager Dashboard.

## For End Users (Managers)

### Uploading/Changing Your Profile Picture

1. **Log in** to the Manager Dashboard at http://localhost:4400 (dev) or your production URL
2. **Click on your avatar** in the top-right corner to open the user menu
3. **Click "Change Avatar"** button in the dropdown menu
4. **Select an image file** from your computer (PNG, JPG, JPEG, GIF, or WebP)
5. Wait for the upload to complete (you'll see "Uploading...")
6. Your new avatar will appear immediately in the top-right corner

### Requirements
- Maximum file size: 5MB
- Supported formats: PNG, JPG, JPEG, GIF, WebP
- Images are automatically resized to 512x512 pixels (aspect ratio maintained)

## For Developers

### Backend Implementation

#### Database Schema
- **Table:** `users`
- **Column:** `avatar_url` (VARCHAR(255), nullable)
- **Migration:** Run `python3 scripts/migrate_add_avatar_url.py` to add the column to existing databases

#### API Endpoints

**Upload Avatar**
```
POST /api/users/me/avatar
Authorization: Bearer <token>
Content-Type: multipart/form-data

Body: file (image file)

Response:
{
  "avatar_url": "/static/avatars/abc123def456.png",
  "message": "Avatar uploaded successfully"
}
```

**Delete Avatar**
```
DELETE /api/users/me/avatar
Authorization: Bearer <token>

Response:
{
  "message": "Avatar deleted successfully"
}
```

**Get Current User** (includes avatar_url)
```
GET /api/auth/me
Authorization: Bearer <token>

Response:
{
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    "avatar_url": "/static/avatars/abc123def456.png",
    ...
  }
}
```

#### File Storage
- **Directory:** `static/avatars/`
- **Naming:** UUIDs (e.g., `abc123def456.png`)
- **Processing:** Images are automatically resized to max 512x512px
- **Old avatars:** Automatically deleted when user uploads a new one

### Frontend Implementation

#### Manager Dashboard
- **Component:** `app.component.ts` and `app.component.html`
- **Service:** `auth.service.ts`
- **Method:** `uploadAvatar(file: File): Observable<any>`

#### Usage in Components
```typescript
// In your component
onAvatarUpload(event: Event): void {
  const input = event.target as HTMLInputElement;
  if (!input.files || input.files.length === 0) return;

  const file = input.files[0];
  this.authService.uploadAvatar(file).subscribe({
    next: (response) => {
      console.log('Avatar uploaded:', response);
      // Refresh user data
      this.authService.validateToken();
    },
    error: (err) => {
      console.error('Upload failed:', err);
    }
  });
}
```

#### Displaying Avatar
```html
<img [src]="currentUser?.avatar_url ? ('http://localhost:8000' + currentUser.avatar_url) : defaultAvatarUrl" 
     alt="Avatar" />
```

### Deployment Considerations

1. **Static Files Directory**
   - Ensure `static/avatars/` directory exists and is writable
   - The directory is created automatically on first upload

2. **Production URL**
   - Update avatar URL prefix from `http://localhost:8000` to your production domain
   - Consider using environment variables for base URL

3. **File Storage Options**
   - Current: Local filesystem storage
   - Alternative: Use cloud storage (S3, CloudFlare R2, etc.) for production
   - Modify `app/api/avatar.py` to upload to cloud storage if needed

4. **Backup Strategy**
   - Include `static/avatars/` in your backup strategy
   - Or use cloud storage that handles backups automatically

### Security Notes

- ✅ File type validation (only images allowed)
- ✅ File size limit (5MB max)
- ✅ Image verification (PIL validates it's a real image)
- ✅ Automatic image resizing (prevents huge files)
- ✅ UUID filenames (prevents path traversal)
- ✅ JWT authentication required
- ✅ Old files automatically deleted

### Troubleshooting

**Avatar not displaying:**
- Check browser console for CORS errors
- Verify static files are mounted correctly (`app.mount("/static", ...)`)
- Check that `static/avatars/` directory has correct permissions

**Upload fails:**
- Check Pillow is installed: `pip install pillow==11.3.0`
- Verify file size is under 5MB
- Check disk space is available
- Review backend logs for detailed error

**Avatar persists after logout:**
- This is expected browser cache behavior
- Avatar URL is fetched fresh on login via `/api/auth/me`
